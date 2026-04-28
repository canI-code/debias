from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import backend.aggregator as aggregator_module
from backend.database import Base
from backend.models import ScoredLog, utcnow


@pytest.mark.asyncio
async def test_build_distribution_table_groups_and_flags(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'agg.db'}", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(aggregator_module, "get_session_maker", lambda: session_maker)
    settings = aggregator_module.get_settings()
    settings.BOOTSTRAP_RESAMPLES = 200
    settings.BOOTSTRAP_CI = 0.95
    settings.RETENTION_DAYS = 1
    async with session_maker() as session:
        session.add_all(
            [
                ScoredLog(
                    log_id="1",
                    toxicity=0.1,
                    identity_attack=0.1,
                    stereotype_score=0.1,
                    refusal_prob=0.0,
                    sentiment=0.2,
                    group_proxy="group-a",
                    intersection_key="group-a|x",
                    scored_at=utcnow(),
                ),
                ScoredLog(
                    log_id="2",
                    toxicity=0.9,
                    identity_attack=0.8,
                    stereotype_score=0.85,
                    refusal_prob=0.2,
                    sentiment=-0.6,
                    group_proxy="group-b",
                    intersection_key="group-b|y",
                    scored_at=utcnow(),
                ),
            ]
        )
        await session.commit()

    frame = await aggregator_module.build_distribution_table_async()
    assert isinstance(frame, pd.DataFrame)
    assert not frame.empty
    assert set(frame["metric_name"]) >= {"toxicity", "stereotype_score", "refusal_prob", "sentiment"}
    assert frame["alert_flag"].any()
    assert frame["low_confidence"].any() is False or frame["low_confidence"].any() is True
    await engine.dispose()


@pytest.mark.asyncio
async def test_small_n_handling_sets_nan_intervals(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'agg-small.db'}", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(aggregator_module, "get_session_maker", lambda: session_maker)
    async with session_maker() as session:
        session.add(
            ScoredLog(
                log_id="1",
                toxicity=0.1,
                identity_attack=0.1,
                stereotype_score=0.1,
                refusal_prob=0.0,
                sentiment=0.2,
                group_proxy="group-a",
                intersection_key="group-a|x",
                scored_at=utcnow(),
            )
        )
        await session.commit()

    frame = await aggregator_module.build_distribution_table_async()
    assert frame.iloc[0]["low_confidence"] is True
    assert pd.isna(frame.iloc[0]["ci_low"])
    assert pd.isna(frame.iloc[0]["ci_high"])
    await engine.dispose()
