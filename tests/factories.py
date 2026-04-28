from __future__ import annotations

import factory


class ChatRequestFactory(factory.Factory):
    class Meta:
        model = dict

    message = factory.Sequence(lambda index: f"Hello from user {index}")
    user_id = factory.Sequence(lambda index: f"user-{index}")
    system_prompt = "You are a helpful assistant."


class ScoredLogPayloadFactory(factory.Factory):
    class Meta:
        model = dict

    log_id = factory.Sequence(lambda index: f"log-{index}")
    request_id = factory.Sequence(lambda index: f"req-{index}")
    user_id_hash = factory.Sequence(lambda index: f"userhash-{index}")
    prompt_hash = factory.Sequence(lambda index: f"prompthash-{index}")
    response_text = "A neutral response about collaboration and respect."
    model = "gpt-4o-mini"
    status = "scored"
    toxicity = 0.1
    identity_attack = 0.05
    stereotype_score = 0.08
    refusal_prob = 0.0
    sentiment = 0.3
    group_proxy = "gender:woman"
    intersection_key = "gender:woman|race:black"
    scored_at = "2026-04-25T00:00:00+00:00"
