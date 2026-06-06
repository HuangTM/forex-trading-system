# QD Rework-1 — Doc Patches for F-003 Externalized Freeze-Receipt

**Author:** quant-developer (QD rework-1)
**Date:** 2026-06-05
**Track:** r5-step3-prereg-2026-06-05 / Phase 1 / Task 1.0
**Purpose:** Item 2(b) — Record the patches needed to fix the self-defeating
`FREEZE BLOCK` section and the §6 retirement criterion.  These are PATCHES ONLY —
do NOT apply them directly.  They require consensus review before application by
the orchestrator.

---

## Problem Statement

The pre-registration document (`references/pre-registrations/r5_carry_universe_kill_test.md`)
currently contains TWO places where the hash-verification logic is self-defeating:

1. **FREEZE BLOCK** (line 1073–1077): The block has three `[FROM FREEZE-RECEIPT]`
   placeholder lines that imply the hash would be embedded in this file. But the hash
   is SHA-256 OF THIS FILE — embedding the hash in the file changes the file, which
   changes the hash. This is a circular dependency that makes the scheme impossible.

2. **§6 retirement criterion** (line 379): The condition
   `freeze_receipt.sha256 != sha256(this_file)` implies the receipt contains a hash
   of the pre-reg file. The variable name `freeze_receipt.sha256` is ambiguous — it
   could read as "the receipt's own sha256" rather than "the sha256 stored in the
   receipt that was computed over the pre-reg file."

**Fix:** The hash lives EXTERNALLY in `r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml`.
The pre-reg file AS COMMITTED (with NO embedded hash) is what is hashed. The receipt
is written by `scripts/cut_freeze_receipt.py` AFTER consensus ratification.

---

## Patch 1 — FREEZE BLOCK section

### ANCHOR (exact text to replace, lines 1073–1078 of the pre-reg doc):

```
# FREEZE BLOCK (filled at assembly by quant-developer — criterion FREEZE-mechanics)

- **Pre-reg SHA-256:** `[FROM FREEZE-RECEIPT]`
- **Pinned code commit (carry_universe_matrix.py + reality_check.py, post-N1):** `[FROM FREEZE-RECEIPT]`
- **Freeze timestamp:** `[FROM FREEZE-RECEIPT]`
- **Signatures:** HoQR · mathematician · quant-developer (code-pin) · NHT (audit) · CEO (ratification) — collected by PM in CONSENSUS_2026-06-05_r5_step3_prereg.md.
```

### REPLACEMENT:

```
# FREEZE BLOCK — criterion FREEZE-mechanics

**Hash integrity model (F-003 fix):** The freeze-receipt lives EXTERNALLY at:

    references/pre-registrations/r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml

The hashed state is THIS FILE AS COMMITTED, WITHOUT any embedded hash — this
document NEVER contains its own hash (embedding the hash would change the file,
changing the hash, making verification impossible).

**Verification rule:**
1. Compute `sha256(bytes of this file as committed)`.
2. That value must equal `receipt.prereg_sha256` in the external FREEZE-RECEIPT.yaml.
3. The git commit of `carry_universe_matrix.py`, `reality_check.py`, and
   `r5_decision.py` (the STEP-4 runner) must equal `receipt.code_commit`.
4. Any edit to this file or those code objects AFTER the receipt is committed
   VOIDS the pre-registration.

The FREEZE-RECEIPT.yaml is written by `scripts/cut_freeze_receipt.py` AFTER
consensus ratification and CEO sign-off.  It is write-once and idempotent-safe
(refuses to overwrite an existing receipt).

- **Signatures:** HoQR · mathematician · quant-developer (code-pin) · NHT (audit) · CEO (ratification) — collected by PM in CONSENSUS_2026-06-05_r5_step3_prereg.md.
```

---

## Patch 2 — §6 retirement criterion (line 379)

### ANCHOR (exact text to replace, line 379 of the pre-reg doc):

```
- `freeze_receipt.sha256 != sha256(this_file) OR freeze_receipt.code_commit != pinned_commit` → **VOID** — the run executed against an unfrozen or drifted spec; result is not face-valid.
```

### REPLACEMENT:

```
- `receipt.prereg_sha256 != sha256(bytes_of_this_prereg_file_as_committed) OR receipt.code_commit != pinned_commit` → **VOID** — the run executed against an unfrozen or drifted spec; result is not face-valid.
  The receipt is the EXTERNAL file `r5_carry_universe_kill_test.FREEZE-RECEIPT.yaml`
  written by `cut_freeze_receipt.py`.  This pre-reg file DOES NOT embed its own hash
  (F-003 fix: embedding the hash would make the scheme circular and impossible to
  satisfy).  Verification: `sha256(this_file_bytes_on_disk) == receipt.prereg_sha256`.
```

---

## Verification Notes for the Orchestrator

Before applying Patch 1:
1. Confirm `cut_freeze_receipt.py` exists at `scripts/cut_freeze_receipt.py`.
2. Confirm `r5_decision.py` exists at `src/forex_system/harness/r5_decision.py`.
3. Run `python3 scripts/cut_freeze_receipt.py --help` (or dry-run) to confirm
   the tool is functional before applying the patch.
4. Apply the FREEZE BLOCK patch to the pre-reg doc.
5. Run `cut_freeze_receipt.py` to generate the receipt.
6. Commit both the patched pre-reg AND the receipt in the same git commit
   (this is the freeze commit; its SHA is captured in `receipt.code_commit`).

After applying Patch 2:
1. Grep for `sha256(this_file)` in the doc — must return no matches.
2. Grep for `freeze_receipt.sha256` in the doc — must return no matches.
3. Grep for `receipt.prereg_sha256` — must appear in the retirement criterion.

---

*These patches are NOT applied in this dispatch (STEP 3).  They are staged here
for orchestrator review and application during the pre-registration finalization
step, before the freeze-receipt is cut.*
