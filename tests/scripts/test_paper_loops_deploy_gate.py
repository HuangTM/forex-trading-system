"""Deploy gate (CRO C1) is enforced by the vol-target and carry_fred paper loops.

Audit backlog 2026-08-17: `assert_deployable` was wired into only 2 of the 4
order-capable loops. These tests drive each loop's real `main()` against the real
shipped config and assert it exits before any broker client is constructed.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

LOOPS = [
    ("scripts.run_paper_trading_vt", "config/vol_target_carry.yaml", "_attach_ws01_file_handler"),
    ("scripts.run_paper_trading_carry_fred", "config/carry_fred.yaml", "_attach_ws02_file_handler"),
]


def _run_main(module_name, attach_fn, argv):
    mod = importlib.import_module(module_name)
    client_cls = MagicMock(side_effect=AssertionError("broker client must not be built"))
    with (
        patch.object(sys, "argv", [module_name, *argv]),
        patch.object(mod, attach_fn),
        patch.object(mod.PaperRunnerBase, "load_last_cycle_ts", return_value=None),
        patch.object(mod, "SaxoClient", client_cls),
    ):
        with pytest.raises(SystemExit) as exc:
            mod.main()
    return exc.value.code, client_cls


@pytest.mark.parametrize("module_name,config_path,attach_fn", LOOPS)
def test_shipped_config_is_flagged_do_not_deploy(module_name, config_path, attach_fn):
    raw = yaml.safe_load((ROOT / config_path).read_text())
    assert raw["deploy_status"]["do_not_deploy"] is True


@pytest.mark.parametrize("module_name,config_path,attach_fn", LOOPS)
def test_loop_refuses_flagged_config_before_broker(module_name, config_path, attach_fn, capsys):
    code, client_cls = _run_main(
        module_name, attach_fn, ["--token", "dummy", "--config", str(ROOT / config_path)]
    )
    assert code == 2
    client_cls.assert_not_called()
    assert "REFUSING TO DEPLOY" in capsys.readouterr().out


@pytest.mark.parametrize("module_name,config_path,attach_fn", LOOPS)
def test_force_falsified_passes_the_gate(module_name, config_path, attach_fn):
    """With the override the gate lets execution reach broker construction."""
    with pytest.raises(AssertionError, match="broker client must not be built"):
        _run_main(
            module_name,
            attach_fn,
            ["--token", "dummy", "--config", str(ROOT / config_path), "--force-falsified"],
        )
