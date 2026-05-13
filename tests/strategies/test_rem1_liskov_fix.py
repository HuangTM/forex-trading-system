"""REM-1 Liskov violation fix — acceptance tests.

Covers:
    REM-1-T1: params-only construction path (all 10 strategies, rate_data=None)
    REM-1-T2: params+rate_data construction path (strategies that use rate_data)
    REM-1-T3: reflection-bypass DELETED assertion (inspect.signature absent)
    N-1-a:    No inspect.signature in scripts/ or src/ (AST-level assertion)
    N-1-b:    No sentinel-default magic-None branching at construction sites
    N-1-c:    No set-membership tests against strategy_name near construction
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pandas as pd
import pytest

from forex_system.strategies.registry import STRATEGY_REGISTRY, create_strategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SRC_DIR = REPO_ROOT / "src"

_BASE_PARAMS = {"pair": "EURUSD"}


def _make_synthetic_rate_data() -> pd.DataFrame:
    """Minimal rate differential DataFrame for testing."""
    idx = pd.date_range("2020-01-01", periods=252, freq="B")
    return pd.DataFrame(
        {
            "EURUSD": [0.01] * len(idx),
            "USDJPY": [0.02] * len(idx),
            "GBPUSD": [-0.005] * len(idx),
            "AUDUSD": [0.005] * len(idx),
            "USDCAD": [-0.01] * len(idx),
            "NZDUSD": [0.003] * len(idx),
            "USDCHF": [-0.007] * len(idx),
            "EURGBP": [0.004] * len(idx),
            "EURJPY": [0.015] * len(idx),
            "GBPJPY": [0.012] * len(idx),
            "AUDJPY": [0.018] * len(idx),
            "NZDJPY": [0.016] * len(idx),
            "CADJPY": [0.013] * len(idx),
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# REM-1-T1: params-only construction — MUST NOT raise for any registered strategy
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("strategy_name", list(STRATEGY_REGISTRY.keys()))
def test_rem1_t1_params_only_construction(strategy_name: str) -> None:
    """REM-1-T1: every strategy constructs via create_strategy(name, params) without
    rate_data. The ABC contract (D-1.1) guarantees rate_data=None is always valid.

    Invariant: no TypeError, no AttributeError on construction.
    """
    strategy = create_strategy(strategy_name, _BASE_PARAMS)
    assert strategy is not None, f"{strategy_name} returned None from create_strategy"
    assert hasattr(strategy, "params"), f"{strategy_name} missing .params attribute"
    assert strategy.params == _BASE_PARAMS, f"{strategy_name} params not stored correctly"


# ---------------------------------------------------------------------------
# REM-1-T2: params+rate_data construction — carry strategies use rate_data kwarg
# ---------------------------------------------------------------------------

_RATE_DATA_STRATEGIES = [
    "carry",
    "carry_fred",
    "carry_momentum",
    "fred_carry_stripped",
    "vol_target_carry",
    "vol_target_carry_no_vol_scaling",
]


@pytest.mark.parametrize("strategy_name", _RATE_DATA_STRATEGIES)
def test_rem1_t2_params_plus_rate_data_construction(strategy_name: str) -> None:
    """REM-1-T2: rate_data-accepting strategies construct via the unified ABC path.

    Invariant: strategy constructs without error and stores rate_data attribute.
    Validates the fix is not a regression on carry/vol strategies.
    """
    rate_data = _make_synthetic_rate_data()
    strategy = create_strategy(strategy_name, _BASE_PARAMS, rate_data=rate_data)
    assert strategy is not None
    # ABC sets self.rate_data in __init__ — all strategies inherit this
    assert strategy.rate_data is not None, (
        f"{strategy_name}.rate_data should not be None when rate_data was injected"
    )


# ---------------------------------------------------------------------------
# REM-1-T3: reflection bypass DELETED
# ---------------------------------------------------------------------------

def test_rem1_t3_reflection_bypass_deleted() -> None:
    """REM-1-T3: _SELF_LOADING_RATE_STRATEGIES and inspect.signature absent.

    Invariant: run_falsification_trial.py contains no inspect.signature and no
    _SELF_LOADING_RATE_STRATEGIES after the REM-1 fix.
    """
    trial_script = SCRIPTS_DIR / "run_falsification_trial.py"
    assert trial_script.exists(), f"Script not found: {trial_script}"
    content = trial_script.read_text()
    assert "inspect.signature" not in content, (
        "inspect.signature found in run_falsification_trial.py — "
        "reflection bypass not fully deleted (REM-1 / D-1.3)"
    )
    assert "_SELF_LOADING_RATE_STRATEGIES" not in content, (
        "_SELF_LOADING_RATE_STRATEGIES allowlist found in run_falsification_trial.py — "
        "allowlist not deleted (REM-1 / D-1.3)"
    )


# ---------------------------------------------------------------------------
# N-1-a: No inspect.signature anywhere in scripts/ or src/
# ---------------------------------------------------------------------------

def _collect_python_files(*dirs: Path) -> list[Path]:
    """Recursively collect all .py files under dirs, excluding test files."""
    files = []
    for d in dirs:
        for f in d.rglob("*.py"):
            # Exclude test files — they may reference forbidden patterns for
            # documentation/assertion purposes without actually using them.
            if f.name.startswith("test_"):
                continue
            files.append(f)
    return files


def test_n1_a_no_inspect_signature_at_construction() -> None:
    """N-1 relocation test (a): inspect.signature must not appear anywhere in
    scripts/ or src/forex_system/. If it does, someone has relocated the
    reflection bypass from run_falsification_trial.py to another site.

    Invariant: ast_grep_count("inspect.signature") == 0 in scripts/ and src/.
    """
    py_files = _collect_python_files(SCRIPTS_DIR, SRC_DIR)
    violations = []
    for fpath in py_files:
        try:
            content = fpath.read_text(errors="replace")
        except OSError:
            continue
        if "inspect.signature" in content:
            violations.append(str(fpath.relative_to(REPO_ROOT)))
    assert not violations, (
        "inspect.signature found in the following files — relocation of REM-1 "
        f"reflection bypass detected (N-1-a):\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# N-1-b: No sentinel-default magic-None branching in strategy construction paths
# ---------------------------------------------------------------------------

def test_n1_b_no_sentinel_magic_none_branching_in_strategy_construction() -> None:
    """N-1 relocation test (b): no 'if rate_data is None:' branch inside
    generate_signals() or __init__() of any strategy that would cause silent
    sentinel-magic behavior at the construction site.

    Invariant: generate_signals() must not branch on 'rate_data is None' in a
    way that changes construction-time behavior (signal-time fallback is allowed
    and expected). The test scans for branches that short-circuit __init__.

    We check __init__ bodies only — signal-time fallback in generate_signals
    is acceptable.
    """
    strategy_src = SRC_DIR / "forex_system" / "strategies"
    py_files = list(strategy_src.rglob("*.py"))
    violations = []

    for fpath in py_files:
        try:
            tree = ast.parse(fpath.read_text(errors="replace"), filename=str(fpath))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name != "__init__":
                continue
            # Look for 'if rate_data is None: ...' branches inside __init__
            for child in ast.walk(node):
                if not isinstance(child, ast.If):
                    continue
                # Check if condition is "rate_data is None" or "rate_data is not None"
                cond = child.test
                if isinstance(cond, ast.Compare):
                    for comp in cond.comparators:
                        if (isinstance(comp, ast.Constant) and comp.value is None
                                and isinstance(cond.left, ast.Name)
                                and "rate_data" in cond.left.id):
                            violations.append(
                                f"{fpath.relative_to(REPO_ROOT)}:{child.lineno} "
                                f"— 'if rate_data is None' in __init__ "
                                f"(magic-None sentinel pattern, N-1-b)"
                            )

    assert not violations, (
        "Sentinel-default magic-None branching detected in __init__ of strategy class(es) "
        "(N-1-b). Move the branch to generate_signals() or handle gracefully at "
        "signal-generation time:\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# N-1-c: No set-membership tests against strategy_name near construction sites
# ---------------------------------------------------------------------------

def test_n1_c_no_strategy_name_set_membership_at_construction() -> None:
    """N-1 relocation test (c): no 'if strategy_name in {...}' patterns near
    strategy construction in scripts/ or src/. This is the relocation of the
    deleted _SELF_LOADING_RATE_STRATEGIES allowlist pattern.

    Invariant: no set-literal membership tests keyed on strategy_name exist
    in the construction path.

    Note: This is a source-text heuristic, not a full AST analysis. It catches
    the most common form of the pattern.
    """
    py_files = _collect_python_files(SCRIPTS_DIR, SRC_DIR)
    # Pattern: variable_name in {string, string, ...} OR variable_name in SCREAMING_CAPS
    # near strategy instantiation contexts
    pattern = re.compile(
        r"strategy[_\w]*\s+in\s+\{['\"][\w_]+['\"]",
        re.IGNORECASE,
    )
    violations = []
    for fpath in py_files:
        try:
            content = fpath.read_text(errors="replace")
        except OSError:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if pattern.search(line):
                violations.append(f"{fpath.relative_to(REPO_ROOT)}:{i}: {line.strip()}")
    assert not violations, (
        "Set-membership test against strategy_name detected (N-1-c) — potential "
        "re-introduction of the _SELF_LOADING_RATE_STRATEGIES allowlist pattern:\n"
        + "\n".join(violations)
    )
