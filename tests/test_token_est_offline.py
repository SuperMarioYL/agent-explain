"""fix-offline-token-estimation (v0.7.0): offline (air-gapped) use must
degrade to an approximation, not crash.

Reproduces the v0.6.0 defect red: both tiktoken encodings download their BPE
from the network on first use, so with no encoding loadable every projection
raised through count_text_tokens and the CLI died with an opaque error.
"""

from __future__ import annotations

import pytest

from agent_explain import token_est


@pytest.fixture()
def offline(monkeypatch):
    """Simulate an air-gapped machine: no tiktoken encoding can be loaded."""
    attempts = []

    def no_network(name):
        attempts.append(name)
        raise RuntimeError("no network connection")

    monkeypatch.setattr(token_est.tiktoken, "get_encoding", no_network)
    monkeypatch.setattr(token_est, "_encoder", None)
    monkeypatch.setattr(token_est, "_encoder_unavailable", False)
    return attempts


def test_count_text_tokens_degrades_instead_of_raising(offline):
    text = "create src/app.py and edit tests/test_app.py" * 10
    n = token_est.count_text_tokens(text)
    assert n > 0
    assert n == len(text.encode("utf-8")) // token_est._BYTES_PER_TOKEN


def test_estimate_step_tokens_completes_offline(offline):
    (low, high), basis = token_est.estimate_step_tokens(
        "read the config and update src/app.py", ["src/app.py"]
    )
    assert low > 0
    assert high > low
    assert basis in ("static", "sampled")


def test_offline_state_latches_and_warns_once(offline, capsys):
    assert token_est._get_encoder() is None
    assert token_est._get_encoder() is None  # latched — no re-attempt
    assert token_est._encoder_unavailable is True
    # exactly the two initial attempts (cl100k_base + gpt2), never more
    assert offline == ["cl100k_base", "gpt2"]
