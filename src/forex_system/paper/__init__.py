"""Paper trading execution module.

REM-2 (CTO D-2.1): This module is the canonical home for paper-trading
infrastructure shared across all per-strategy paper runners.

Contents:
    base_runner.py — PaperRunnerBase class (BC-8-LIFT-COND-1..7 risk envelope)

Phase-A dispatch (2026-05-13):
    Only BC-8-LIFT-COND-1 (kill switch hook) is extracted.
    COND-2..7 are documented as TODO in base_runner.py pending follow-up dispatch.
    Neither run_paper_trading_vt.py nor run_paper_trading_carry_fred.py
    migrates to use PaperRunnerBase yet — that is the full REM-2 extraction
    (5-10 days per CTO D-2.3 effort estimate).
"""
