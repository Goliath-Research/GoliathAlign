"""GOLIATH_ALIGN_* dual-read helper."""

from __future__ import annotations


def test_getenv_prefers_goliath_align(monkeypatch):
    from mojo_align_env import getenv

    monkeypatch.setenv("GOLIATH_ALIGN_READ_BATCH", "16")
    monkeypatch.setenv("MOJO_ALIGN_READ_BATCH", "8")
    monkeypatch.setenv("METHYLGRAPHER_MOJO_READ_BATCH", "99")
    assert getenv("READ_BATCH") == "16"


def test_getenv_falls_back_to_mojo_align(monkeypatch):
    from mojo_align_env import getenv

    monkeypatch.delenv("GOLIATH_ALIGN_READ_BATCH", raising=False)
    monkeypatch.setenv("MOJO_ALIGN_READ_BATCH", "32")
    monkeypatch.setenv("METHYLGRAPHER_MOJO_READ_BATCH", "99")
    assert getenv("READ_BATCH") == "32"


def test_getenv_falls_back_to_legacy(monkeypatch):
    from mojo_align_env import getenv

    monkeypatch.delenv("GOLIATH_ALIGN_READ_BATCH", raising=False)
    monkeypatch.delenv("MOJO_ALIGN_READ_BATCH", raising=False)
    monkeypatch.setenv("METHYLGRAPHER_MOJO_READ_BATCH", "4")
    assert getenv("READ_BATCH") == "4"
