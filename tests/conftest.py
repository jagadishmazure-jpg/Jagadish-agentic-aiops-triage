import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture(scope="session")
def metrics():
    return json.loads((ROOT / "results/metrics.json").read_text())


@pytest.fixture(scope="session")
def incidents():
    return [json.loads(x) for x in (ROOT / "data/incidents.jsonl").read_text().splitlines()]


@pytest.fixture(scope="session")
def by_id(incidents):
    return {i["id"]: i for i in incidents}


class FakeLLM:
    """Replays scripted replies; records the messages it was shown."""

    def __init__(self, replies, tokens_per_byte=0.0):
        self.replies, self.seen, self.tpb = list(replies), [], tokens_per_byte

    def create_chat_completion(self, messages, **kw):
        self.seen.append([dict(m) for m in messages])
        text = self.replies.pop(0) if self.replies else "I am thinking."
        return {"choices": [{"message": {"content": text}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}

    def tokenize(self, b):
        return [0] * int(len(b) * self.tpb)
