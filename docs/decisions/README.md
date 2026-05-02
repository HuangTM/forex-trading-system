# Decisions log

Signed CONSENSUS documents from `/fintech-org` orchestration runs. Each file
records a multi-role consensus (CTO, CRO, HoQR, NHT, PM, ...) plus CEO ratification
on a specific decision.

## Index

| File | Date | Subject |
|------|------|---------|
| [CONSENSUS.md](CONSENSUS.md) | (pre-2026-04-25) | Original gate chain + top-improvements list |
| [CONSENSUS_2026-04-25.md](CONSENSUS_2026-04-25.md) | 2026-04-25 | vol_target_carry validation + retirement contract VTC-T1..T8 |
| [CONSENSUS_2026-04-28.md](CONSENSUS_2026-04-28.md) | 2026-04-28 | Direction v1 (12-week roadmap, carry thesis, NHT dissent preserved) |
| [CONSENSUS_2026-05-01_phase2_falsification.md](CONSENSUS_2026-05-01_phase2_falsification.md) | 2026-05-01 | Phase 2 falsification trials — frozen rubric (R1–R6), 7-item queue, harness spec; awaiting CEO ratification |
| [CONSENSUS_2026-05-01_phase2_closure.md](CONSENSUS_2026-05-01_phase2_closure.md) | 2026-05-01 | Phase 2 closure — 7-trial outcomes (6 REJECTs + 1 WEAK PASS), carry thesis validated (R7 NOT fired), Tier A satisfied, Tier B 6/10, Wave-5 BLOCKED on 3 conditions; awaiting CEO ratification |

## Migration history

These files lived at the repo root until **2026-04-28** when CTO CONDITION-3 of
`CONSENSUS_2026-04-28.md` migrated them here ("CONSENSUS docs migrated to
`docs/decisions/` and root cleaned within current sprint").

### Known stale references — historical, not bugs

`RETIREMENT_DECISION_2026-04-25.md` (still at repo root) contains line-pinned
references to `CONSENSUS.md`:

- `CONSENSUS.md:151-167` — VTC-T1..T8 retirement triggers
- `CONSENSUS.md:96` — engine reference
- `CONSENSUS.md:139` — equivalence assumption
- `CONSENSUS.md:200` — pre-CONSENSUS process violation note
- `CONSENSUS.md:392` — orchestrator instruction note

These line numbers refer to the *state of `CONSENSUS.md` at the time the retirement
decision was authored on 2026-04-25*. They are **intentionally not updated** to
preserve the audit trail. Read them as historical pointers, not live links.

If you are reviewing the retirement decision and need to read the corresponding
sections in `CONSENSUS.md`, search the file by section header rather than by
line number — the line numbers may not match in the migrated copy if any
line-ending or trailing-whitespace normalization has occurred.

## Convention going forward

- New CONSENSUS docs land directly here, **not at the repo root**.
- Filename: `CONSENSUS_YYYY-MM-DD.md` (or topical suffix if multiple per day).
- Cross-references from anywhere in the repo should use the full path
  `docs/decisions/CONSENSUS*.md`, not bare filenames.
