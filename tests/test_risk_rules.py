"""Tests for the rule-based risk classifier."""

from agent_explain.risk_rules import classify_risk


def test_benign_format_verb_is_not_high_risk():
    """Benign 'format the code/output' steps must NOT be HIGH.

    Regression for fix-format-verb-false-high-risk (v0.5.0): the bare
    ``format`` token was dropped from ``_HIGH_PATTERNS`` (it matched benign
    uses and, via the most-dangerous-pattern-wins rule, classified a "run
    black to format the code" step the same as ``rm -rf`` / ``mkfs``).
    """
    assert classify_risk("Run black to format the code.") != "high"
    assert classify_risk("Format the output as JSON.") != "high"
    assert classify_risk("Use a string format template.") != "high"


def test_benign_format_falls_through_to_medium_when_run_present():
    """'format the code' alongside 'run' classifies MEDIUM, not HIGH."""
    assert classify_risk("Run black to format the code.") == "medium"


def test_disk_format_command_still_high_risk():
    """Direct disk-format commands must stay HIGH via the scoped pattern.

    Dropping the bare ``format`` token must not lose disk-format coverage;
    the scoped ``format <disk-target>`` pattern (plus ``fdisk``/``mkfs``)
    preserves it.
    """
    assert classify_risk("format /dev/sda1") == "high"
    assert classify_risk("format sdz") == "high"
    assert classify_risk("mkfs.ext4 /dev/sda1") == "high"
    assert classify_risk("fdisk /dev/sda") == "high"
