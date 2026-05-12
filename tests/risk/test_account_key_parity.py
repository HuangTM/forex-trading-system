"""Tests for src/forex_system/risk/account_key_parity.py (W11-1)."""

from __future__ import annotations

import json

import pytest

from forex_system.risk.account_key_parity import (
    assert_account_key_parity,
    reset_account_key_lock,
)


def test_first_call_creates_lock_file(tmp_path):
    """Test 1: first call with a new lock_path atomically creates the lock file."""
    lock = str(tmp_path / "aklock.json")
    assert_account_key_parity("key_A", loop_name="vt loop", lock_path=lock)
    data = json.loads(open(lock).read())
    assert data["account_key"] == "key_A"


def test_second_call_same_key_passes(tmp_path):
    """Test 2: second call with the same key is silent (no exception)."""
    lock = str(tmp_path / "aklock.json")
    assert_account_key_parity("key_A", loop_name="vt loop", lock_path=lock)
    # Should not raise
    assert_account_key_parity("key_A", loop_name="vt loop", lock_path=lock)


def test_second_call_different_key_exits_with_vt_discriminator(tmp_path):
    """Test 3: mismatched key raises SystemExit with 'vt loop' in the message."""
    lock = str(tmp_path / "aklock.json")
    assert_account_key_parity("key_A", loop_name="vt loop", lock_path=lock)
    with pytest.raises(SystemExit) as exc_info:
        assert_account_key_parity("key_B", loop_name="vt loop", lock_path=lock)
    assert exc_info.value.code == 1


def test_second_call_different_key_exits_with_carry_fred_discriminator(tmp_path, capsys):
    """Test 4: mismatched key raises SystemExit and 'carry_fred loop' appears in FATAL output."""
    lock = str(tmp_path / "aklock.json")
    assert_account_key_parity("key_A", loop_name="carry_fred loop", lock_path=lock)
    with pytest.raises(SystemExit) as exc_info:
        assert_account_key_parity("key_B", loop_name="carry_fred loop", lock_path=lock)
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "carry_fred loop" in captured.out


def test_vt_discriminator_appears_in_fatal_output(tmp_path, capsys):
    """Test 3b: 'vt loop' discriminator string is rendered verbatim in the FATAL message."""
    lock = str(tmp_path / "aklock.json")
    assert_account_key_parity("key_A", loop_name="vt loop", lock_path=lock)
    with pytest.raises(SystemExit):
        assert_account_key_parity("key_B", loop_name="vt loop", lock_path=lock)
    captured = capsys.readouterr()
    assert "vt loop" in captured.out


def test_reset_overwrites_existing_lock(tmp_path):
    """Test 5a: reset_account_key_lock replaces an existing lock file with the new key."""
    lock = str(tmp_path / "aklock.json")
    assert_account_key_parity("key_A", loop_name="vt loop", lock_path=lock)
    with pytest.raises(SystemExit) as exc_info:
        reset_account_key_lock("new_key", lock_path=lock)
    assert exc_info.value.code == 0
    data = json.loads(open(lock).read())
    assert data["account_key"] == "new_key"


def test_reset_creates_lock_when_absent(tmp_path):
    """Test 5b: reset_account_key_lock creates the lock file when it doesn't exist yet."""
    lock = str(tmp_path / "aklock.json")
    with pytest.raises(SystemExit) as exc_info:
        reset_account_key_lock("brand_new_key", lock_path=lock)
    assert exc_info.value.code == 0
    data = json.loads(open(lock).read())
    assert data["account_key"] == "brand_new_key"


def test_reset_allows_subsequent_parity_check(tmp_path):
    """Test 5c: after reset, assert_account_key_parity accepts the new key."""
    lock = str(tmp_path / "aklock.json")
    assert_account_key_parity("key_A", loop_name="vt loop", lock_path=lock)
    with pytest.raises(SystemExit):
        reset_account_key_lock("key_B", lock_path=lock)
    # Now key_B should pass
    assert_account_key_parity("key_B", loop_name="vt loop", lock_path=lock)
