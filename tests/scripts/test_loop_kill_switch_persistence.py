"""Every order-capable loop must build its KillSwitch with a persistent audit log.

Audit backlog 2026-08-17: run_paper_trading.py and run_multi_strategy.py built
`KillSwitch(initial_equity=...)` with no audit log, so a HALT was forgotten on restart.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from forex_system.risk.kill_switch import KillSwitch, TriggerReason  # noqa: E402

LOOPS = [
    "scripts/run_paper_trading.py",
    "scripts/run_multi_strategy.py",
    "scripts/run_paper_trading_vt.py",
    "scripts/run_paper_trading_carry_fred.py",
]


def _kill_switch_calls(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text())
    return [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "KillSwitch"
    ]


def _audit_target(call: ast.Call) -> str:
    kw = {k.arg: k.value for k in call.keywords}
    if "audit_log_path" in kw:
        return ast.literal_eval(kw["audit_log_path"])
    return f"data/kill_switch_audit_{ast.literal_eval(kw['strategy_id'])}.log"


@pytest.mark.parametrize("loop", LOOPS)
def test_loop_kill_switch_is_persistent(loop):
    calls = _kill_switch_calls(ROOT / loop)
    assert calls, f"{loop}: no KillSwitch construction found"
    for call in calls:
        kws = {k.arg for k in call.keywords}
        assert kws & {"audit_log_path", "strategy_id"}, (
            f"{loop}:{call.lineno}: KillSwitch without audit_log_path/strategy_id "
            "forgets a HALT on restart"
        )


def test_loops_do_not_share_an_audit_log():
    targets = [_audit_target(c) for loop in LOOPS for c in _kill_switch_calls(ROOT / loop)]
    assert len(targets) == len(set(targets)), targets


def test_halt_survives_restart_under_strategy_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KILL_SWITCH_FORCE_RESET", raising=False)
    (tmp_path / "data").mkdir()
    ks = KillSwitch(initial_equity=100_000, strategy_id="paper_portfolio")
    ks.trigger(TriggerReason.MANUAL, detail="test halt", equity=95_000)
    log = tmp_path / "data/kill_switch_audit_paper_portfolio.log"
    assert "HALTED" in json.loads(log.read_text().splitlines()[-1])["new_state"]
    with pytest.raises(RuntimeError, match="HALTED"):
        KillSwitch(initial_equity=100_000, strategy_id="paper_portfolio")
