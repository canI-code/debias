"""One-time backfill: score all existing chat logs and run aggregation."""
from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime

sys.path.insert(0, ".")

from sqlalchemy import select

from backend.aggregator import build_distribution_table_async
from backend.database import get_session_maker, init_db
from backend.models import ChatLog, MetricSnapshot, ScoredLog
from backend.utils import sanitize_prompt
from backend.worker import (
    _extract_proxies,
    _score_refusal,
    _score_sentiment,
    _score_stereotype,
    _score_toxicity,
)


def score_one(response_text: str, prompt_hash: str) -> dict:
    prompt = sanitize_prompt(prompt_hash or "")
    response = sanitize_prompt(response_text or "")
    combined = f"{prompt} {response}".strip() or "neutral"
    scoring_text = response or "neutral"
    tox, id_atk = _score_toxicity(scoring_text)
    stereo = _score_stereotype(combined)
    refusal = _score_refusal(scoring_text)
    sentiment = _score_sentiment(scoring_text)
    gp, ik = _extract_proxies(combined)
    return {
        "toxicity": tox,
        "identity_attack": id_atk,
        "stereotype_score": stereo,
        "refusal_prob": refusal,
        "sentiment": sentiment,
        "group_proxy": gp,
        "intersection_key": ik,
    }


async def main() -> None:
    await init_db()
    sm = get_session_maker()

    async with sm() as s:
        chat_rows = list((await s.scalars(select(ChatLog))).all())
        scored_ids = set((await s.scalars(select(ScoredLog.log_id))).all())

    unscored = [r for r in chat_rows if r.id not in scored_ids]
    print(f"Chats total: {len(chat_rows)}, unscored: {len(unscored)}")

    if not unscored:
        print("Nothing to backfill.")
    else:
        async with sm() as s:
            for row in unscored:
                scores = await asyncio.to_thread(score_one, row.response_text or "", row.prompt_hash or "")
                s.add(ScoredLog(
                    log_id=row.id,
                    toxicity=float(scores["toxicity"]),
                    identity_attack=float(scores["identity_attack"]),
                    stereotype_score=float(scores["stereotype_score"]),
                    refusal_prob=float(scores["refusal_prob"]),
                    sentiment=float(scores["sentiment"]),
                    group_proxy=str(scores["group_proxy"]),
                    intersection_key=str(scores["intersection_key"]),
                    scored_at=datetime.now(UTC),
                ))
                print(f"  Scored {row.id[:12]}  tox={scores['toxicity']:.3f}  stereo={scores['stereotype_score']:.3f}")
            await s.commit()
        print(f"\nScored {len(unscored)} logs.")

    print("\nRunning aggregation...")
    df = await build_distribution_table_async()
    print(f"Aggregation produced {len(df)} metric rows.")

    async with sm() as s:
        snap_count = (await s.execute(
            select(MetricSnapshot.id)
        )).scalars().all()
    print(f"MetricSnapshots in DB: {len(snap_count)}")
    print("\nDone! Refresh the dashboard now.")


if __name__ == "__main__":
    asyncio.run(main())
