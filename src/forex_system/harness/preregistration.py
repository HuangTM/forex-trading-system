"""Pre-registration parser for the falsification harness.

Design: sidecar YAML approach
------------------------------
Each pre-reg markdown has a paired `<basename>.triggers.yaml` sidecar with
structured, machine-checkable trigger definitions. The markdown holds prose;
the sidecar holds typed data. Absent sidecar → ConfigError (never silently
omitted).

API
---
    parse_pre_registration(pre_reg_path, sidecar_path=None) -> PreRegistrationSpec

    @dataclass(frozen=True) FalsificationTrigger
    @dataclass(frozen=True) PreRegistrationSpec

Parsing rules (sourced from qd-harness-spec.yaml Wave 2)
----------------------------------------------------------
- kill_switch_threshold: regex r"kill_switch_threshold:\\s*(\\S+)", raw string.
- gate_threshold: regex r"gate_threshold:\\s*([\\d.]+)", cast to float, None if absent.
- strategy: from **Strategy ID:** line.
- pair: from **Pair:** line.
- hypothesis_summary: first non-empty paragraph under ## Hypothesis section.
- oos_overlap: bool from sidecar YAML (key: oos_overlap).
- oos_window_start/end: ISO date strings from sidecar YAML.
- triggers: loaded entirely from sidecar YAML triggers list.

Decision trace
--------------
Emits a structured log line (log-as-decision-trace) with all parsed field
values so a future reader can confirm the spec loaded at trial-start.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from forex_system.core.errors import ConfigError

logger = logging.getLogger("forex_system.harness.preregistration")


def _log_event(event: str, **fields: object) -> None:
    """Emit a structured decision-trace log line (JSON)."""
    entry = {
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    logger.info(json.dumps(entry))


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FalsificationTrigger:
    """A single machine-checkable falsification trigger.

    Attributes
    ----------
    label:
        Trigger label, e.g. "VTC-T1", "R3-T1". Used in trial records.
    metric:
        Metric key evaluated against the backtest result dict, e.g.
        "oos_sharpe", "max_drawdown", "dsr", "n_trades".
    operator:
        Comparison operator: one of "<", ">", "<=", ">=".
    threshold:
        Numeric threshold; trigger fires when metric <operator> threshold is True.
    raw_text:
        Original bullet text from the markdown pre-reg (for human audit log).
        May be empty string if label not found in markdown.
    """

    label: str
    metric: str
    operator: str
    threshold: float
    raw_text: str

    def __post_init__(self) -> None:
        if self.operator not in ("<", ">", "<=", ">="):
            raise ConfigError(
                f"FalsificationTrigger '{self.label}': operator must be one of "
                f"'<', '>', '<=', '>=' — got '{self.operator}'."
            )


@dataclass(frozen=True)
class PreRegistrationSpec:
    """Typed, machine-checkable pre-registration specification.

    Attributes
    ----------
    strategy:
        Strategy ID matching the trial registry (e.g. "vol_target_carry").
    pair:
        Currency pair free-text from markdown **Pair:** field (informational;
        e.g. "EURUSD, USDJPY, GBPUSD"). Authoritative pair list is in
        ``pair_resolved``.
    pair_resolved:
        Authoritative list of currency pairs from the sidecar YAML ``pair``
        field. Expanded from shorthand: ``all`` → Phase-2 universe
        ["EURUSD", "USDJPY", "GBPUSD"]; single string → one-element list;
        YAML list → list as-is. ConfigError raised if absent from sidecar.
    hypothesis_summary:
        First non-empty paragraph under ## Hypothesis section.
    kill_switch_threshold:
        Raw string from kill_switch_threshold: field (NOT cast to float;
        may be a label like "VTC-T1" or a numeric string like "0.60").
        Trailing backticks and whitespace are stripped at parse time.
    gate_threshold:
        Parsed float from gate_threshold: field, or None if absent.
    triggers:
        Ordered list of FalsificationTrigger instances (from sidecar YAML).
    oos_overlap:
        True if this strategy's OOS window overlaps with a validated strategy.
        Sourced from sidecar YAML (required field per NHT Conflict-2 protection).
    oos_window_start:
        ISO date string for the OOS window start (from sidecar YAML).
    oos_window_end:
        ISO date string for the OOS window end (from sidecar YAML).
    """

    strategy: str
    pair: str
    pair_resolved: tuple[str, ...]
    hypothesis_summary: str
    kill_switch_threshold: str
    gate_threshold: float | None
    triggers: tuple[FalsificationTrigger, ...]
    oos_overlap: bool
    oos_window_start: str
    oos_window_end: str
    timeframe: str = "daily"
    data_dir: str = "data"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Phase-2 instrument universe — expanded when sidecar declares pair: all.
_PHASE2_UNIVERSE: tuple[str, ...] = ("EURUSD", "USDJPY", "GBPUSD")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _extract_field(text: str, pattern: str, field_name: str) -> str | None:
    """Extract first capture group from text using regex, or return None.

    Strips surrounding backticks and whitespace from the captured value so that
    inline-code-formatted values (e.g. ``kill_switch_threshold: 0.30``) are
    returned as plain strings without trailing backticks.
    """
    m = re.search(pattern, text)
    if not m:
        return None
    return m.group(1).strip("`").strip()


def _extract_hypothesis_summary(text: str) -> str:
    """Extract first non-empty paragraph under ## Hypothesis section."""
    lines = text.splitlines()
    in_hypothesis = False
    paragraph_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        # Detect section header
        if re.match(r"^##\s+Hypothesis", stripped, re.IGNORECASE):
            in_hypothesis = True
            continue
        # Stop at next section
        if in_hypothesis and re.match(r"^##\s+", stripped):
            break
        if in_hypothesis:
            if stripped:
                paragraph_lines.append(stripped)
            elif paragraph_lines:
                # Non-empty paragraph collected; stop at first blank line after content.
                break

    return " ".join(paragraph_lines)


def _extract_trigger_raw_texts(text: str) -> dict[str, str]:
    """Extract raw bullet texts from markdown, keyed by trigger label.

    Matches lines like: - **VTC-T1:** ... or - VTC-T1: ...
    """
    result: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*[-*]\s+\*?\*?([A-Z]+-T\d+)\*?\*?:?\s*(.*)", line)
        if m:
            label = m.group(1)
            raw = m.group(2).strip()
            result[label] = raw
    return result


def _parse_sidecar(sidecar_path: Path, markdown_raw_texts: dict[str, str]) -> dict:
    """Parse the sidecar YAML and validate required fields.

    Returns a dict with keys: triggers, oos_overlap, oos_window_start, oos_window_end.
    Raises ConfigError if the YAML is missing, invalid, or missing required fields.
    """
    if not sidecar_path.exists():
        raise ConfigError(
            f"Pre-registration sidecar not found: {sidecar_path}\n"
            "Each pre-reg markdown requires a paired .triggers.yaml sidecar with "
            "structured trigger definitions. Create the sidecar before registering a trial."
        )

    try:
        raw = yaml.safe_load(sidecar_path.read_text())
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"Pre-registration sidecar is invalid YAML: {sidecar_path}\nError: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise ConfigError(
            f"Pre-registration sidecar must be a YAML mapping: {sidecar_path}"
        )

    # Validate required fields.
    for required in ("triggers", "oos_overlap", "oos_window_start", "oos_window_end", "pair"):
        if required not in raw:
            raise ConfigError(
                f"Pre-registration sidecar missing required field '{required}': {sidecar_path}"
            )

    if not isinstance(raw["oos_overlap"], bool):
        raise ConfigError(
            f"Sidecar field 'oos_overlap' must be a boolean (true/false): {sidecar_path}"
        )

    # Resolve pair from sidecar (authoritative; DO NOT silently default).
    sidecar_pair = raw["pair"]
    if isinstance(sidecar_pair, str):
        pair_str = sidecar_pair.strip()
        if pair_str.lower() == "all":
            pair_resolved: tuple[str, ...] = _PHASE2_UNIVERSE
        else:
            pair_resolved = (pair_str.upper(),)
    elif isinstance(sidecar_pair, list):
        if not sidecar_pair:
            raise ConfigError(
                f"Sidecar field 'pair' is an empty list: {sidecar_path}"
            )
        pair_resolved = tuple(str(p).strip().upper() for p in sidecar_pair)
    else:
        raise ConfigError(
            f"Sidecar field 'pair' must be a string or list, got "
            f"{type(sidecar_pair).__name__}: {sidecar_path}"
        )

    # Parse triggers list.
    triggers_raw = raw.get("triggers", [])
    if not isinstance(triggers_raw, list):
        raise ConfigError(
            f"Sidecar field 'triggers' must be a list: {sidecar_path}"
        )

    triggers: list[FalsificationTrigger] = []
    for i, trig in enumerate(triggers_raw):
        for tfield in ("label", "metric", "operator", "threshold"):
            if tfield not in trig:
                raise ConfigError(
                    f"Sidecar trigger[{i}] missing required field '{tfield}': {sidecar_path}"
                )
        label = str(trig["label"])
        raw_text = markdown_raw_texts.get(label, "")
        triggers.append(
            FalsificationTrigger(
                label=label,
                metric=str(trig["metric"]),
                operator=str(trig["operator"]),
                threshold=float(trig["threshold"]),
                raw_text=raw_text,
            )
        )

    result: dict = {
        "triggers": triggers,
        "pair_resolved": pair_resolved,
        "oos_overlap": bool(raw["oos_overlap"]),
        "oos_window_start": str(raw["oos_window_start"]),
        "oos_window_end": str(raw["oos_window_end"]),
    }

    # Optional fields: surface to caller if present (used by grandfathered pre-regs).
    if "kill_switch_threshold" in raw:
        result["kill_switch_threshold"] = str(raw["kill_switch_threshold"])
    if "timeframe" in raw:
        result["timeframe"] = str(raw["timeframe"])
    if "data_dir" in raw:
        result["data_dir"] = str(raw["data_dir"])

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_pre_registration(
    pre_reg_path: Path,
    sidecar_path: Path | None = None,
) -> PreRegistrationSpec:
    """Parse a pre-reg markdown + sidecar YAML into a typed PreRegistrationSpec.

    Parameters
    ----------
    pre_reg_path:
        Path to the .md file. ConfigError if absent.
    sidecar_path:
        Path to the .triggers.yaml sidecar. If None, defaults to
        pre_reg_path.with_suffix('.triggers.yaml').
        ConfigError if sidecar is absent (triggers are mandatory).

    Returns
    -------
    PreRegistrationSpec
        Fully typed, immutable spec ready for falsification evaluation.

    Raises
    ------
    ConfigError
        If the markdown is missing, the sidecar is missing/invalid, or
        any required field cannot be parsed.

    Decision trace
    --------------
    Emits trial.pre_reg.parsed log event with all parsed field values.
    """
    if not pre_reg_path.exists():
        raise ConfigError(
            f"Pre-registration markdown not found: {pre_reg_path}"
        )

    if sidecar_path is None:
        sidecar_path = pre_reg_path.with_suffix(".triggers.yaml")

    text = pre_reg_path.read_text()

    # --- Parse markdown fields ---
    strategy = _extract_field(text, r"\*\*Strategy ID:\*\*\s*(\S+)", "strategy")
    if not strategy:
        raise ConfigError(
            f"Could not parse '**Strategy ID:**' from: {pre_reg_path}\n"
            "Add a line '**Strategy ID:** <strategy_id>' to the pre-reg."
        )

    pair = _extract_field(text, r"\*\*Pair:\*\*\s*(\S+)", "pair")
    # pair may be None for grandfathered pre-regs without a **Pair:** line;
    # the sidecar's pair_resolved list is the authoritative source in that case.
    # We defer the fallback until after sidecar parsing.

    kill_switch_threshold = _extract_field(
        text, r"kill_switch_threshold:\s*(\S+)", "kill_switch_threshold"
    )
    # Note: kill_switch_threshold may be absent in grandfathered pre-regs that use
    # older gate_threshold convention (e.g. tas_ceiling_4h.md). If absent from
    # markdown, we fall back to the sidecar's kill_switch_threshold field after
    # sidecar parsing below. Do NOT raise here for absent kill_switch_threshold;
    # the check is deferred to post-sidecar.

    gate_threshold_str = _extract_field(text, r"gate_threshold:\s*([\d.]+)", "gate_threshold")
    gate_threshold = float(gate_threshold_str) if gate_threshold_str is not None else None

    hypothesis_summary = _extract_hypothesis_summary(text)

    # --- Parse sidecar ---
    markdown_raw_texts = _extract_trigger_raw_texts(text)
    sidecar_data = _parse_sidecar(sidecar_path=sidecar_path, markdown_raw_texts=markdown_raw_texts)

    # kill_switch_threshold fallback: if absent from markdown, accept from sidecar
    # (Path B for grandfathered pre-regs like tas_ceiling_4h that use gate_threshold).
    if not kill_switch_threshold:
        sidecar_kst = sidecar_data.get("kill_switch_threshold")
        if sidecar_kst:
            kill_switch_threshold = str(sidecar_kst)
    if not kill_switch_threshold:
        raise ConfigError(
            f"Could not parse 'kill_switch_threshold:' from: {pre_reg_path}\n"
            "Add 'kill_switch_threshold: <value>' to the pre-reg markdown or "
            "to the paired .triggers.yaml sidecar (Path B for grandfathered pre-regs)."
        )

    # Pair fallback: if markdown has no **Pair:** line, synthesize from sidecar pair_resolved.
    if not pair:
        pair = ", ".join(sidecar_data["pair_resolved"])

    spec = PreRegistrationSpec(
        strategy=strategy,
        pair=pair,
        pair_resolved=sidecar_data["pair_resolved"],
        hypothesis_summary=hypothesis_summary,
        kill_switch_threshold=kill_switch_threshold,
        gate_threshold=gate_threshold,
        triggers=tuple(sidecar_data["triggers"]),
        oos_overlap=sidecar_data["oos_overlap"],
        oos_window_start=sidecar_data["oos_window_start"],
        oos_window_end=sidecar_data["oos_window_end"],
        timeframe=sidecar_data.get("timeframe", "daily"),
        data_dir=sidecar_data.get("data_dir", "data"),
    )

    _log_event(
        "trial.pre_reg.parsed",
        pre_reg_path=str(pre_reg_path),
        sidecar_path=str(sidecar_path),
        strategy=spec.strategy,
        pair=spec.pair,
        pair_resolved=list(spec.pair_resolved),
        kill_switch_threshold=spec.kill_switch_threshold,
        gate_threshold=spec.gate_threshold,
        n_triggers=len(spec.triggers),
        trigger_labels=[t.label for t in spec.triggers],
        oos_overlap=spec.oos_overlap,
        oos_window_start=spec.oos_window_start,
        oos_window_end=spec.oos_window_end,
    )

    return spec
