"""
QD numerical confirmation script for r5-confirmatory-2026-06-06:phase1:task1.0
Confirms all hand values from mathematician-conf-spec.yaml via scipy.
Pure math — no market data, no backtests.
"""
import math
import numpy as np
from scipy import stats
from scipy.optimize import brentq

print("=" * 70)
print("QD SCIPY CONFIRMATION — r5-confirmatory-2026-06-06")
print("=" * 70)

# ─────────────────────────────────────────────────────────────────
# STEP 5 (sanity first): Φ⁻¹(0.95) and the frozen dispersion
# ─────────────────────────────────────────────────────────────────
z_95 = stats.norm.ppf(0.95)
dispersion = 0.426385  # FROZEN — NOT re-derived
gamma = 0.5772156649   # Euler-Mascheroni
e_const = math.e

print(f"\n[SANITY]")
print(f"  Φ⁻¹(0.95)          = {z_95:.6f}  (expected 1.644854)")
print(f"  dispersion (frozen) = {dispersion}  (NOT re-derived)")

# ─────────────────────────────────────────────────────────────────
# STEP 1: BLdP SR0 bracket(N=6)
# ─────────────────────────────────────────────────────────────────
N_conf = 6

# Two quantile arguments
arg1 = 1.0 - 1.0 / N_conf                 # = 5/6 = 0.833333...
arg2 = 1.0 - 1.0 / (N_conf * e_const)     # = 1 - 1/(6e)

z_arg1 = stats.norm.ppf(arg1)
z_arg2 = stats.norm.ppf(arg2)

bracket_6 = (1.0 - gamma) * z_arg1 + gamma * z_arg2
sr0_ann = dispersion * bracket_6
sr0_pp = sr0_ann / math.sqrt(252)

print(f"\n[STEP 1] BLdP SR0 bracket(N=6)")
print(f"  arg1 = 1 - 1/6          = {arg1:.8f}")
print(f"  arg2 = 1 - 1/(6e)       = {arg2:.8f}")
print(f"  Z⁻¹(arg1)               = {z_arg1:.6f}  (hand: 0.967422)")
print(f"  Z⁻¹(arg2)               = {z_arg2:.6f}  (hand: 1.542968)")
print(f"  (1-γ)                   = {1-gamma:.7f}")
print(f"  γ                       = {gamma:.7f}")
print(f"  (1-γ)·Z⁻¹(arg1)         = {(1-gamma)*z_arg1:.6f}  (hand: 0.409013)")
print(f"  γ·Z⁻¹(arg2)             = {gamma*z_arg2:.6f}  (hand: 0.890636)")
print(f"  bracket(6)              = {bracket_6:.6f}  (hand: 1.299649)")
print(f"  SR0_ann_conf            = {sr0_ann:.6f}  (hand: 0.554150)")
print(f"  SR0_pp_conf             = {sr0_pp:.6f}  (hand: 0.034908)")

# ─────────────────────────────────────────────────────────────────
# STEP 2: Lan-DeMets sfLDOF (OBF-type) boundaries
# ─────────────────────────────────────────────────────────────────
# One-sided total alpha = 0.05
# Spending function: α*(t) = 2·(1 − Φ(Φ⁻¹(1−α/2) / sqrt(t)))
alpha_total = 0.05
alpha_half = alpha_total / 2.0            # 0.025

z_alpha_half = stats.norm.ppf(1.0 - alpha_half)    # = Φ⁻¹(0.975) = 1.959964

# Cumulative spend at t=0.5
t1 = 0.5
spend_t05 = 2.0 * (1.0 - stats.norm.cdf(z_alpha_half / math.sqrt(t1)))
# Cumulative spend at t=1.0 (should equal 0.05 exactly)
t2 = 1.0
spend_t10 = 2.0 * (1.0 - stats.norm.cdf(z_alpha_half / math.sqrt(t2)))
incremental_spend_1 = spend_t05
incremental_spend_2 = spend_t10 - spend_t05

print(f"\n[STEP 2] Lan-DeMets sfLDOF boundaries (one-sided α=0.05, t=[0.5,1.0])")
print(f"  Φ⁻¹(1−α/2) = Φ⁻¹(0.975) = {z_alpha_half:.6f}")
print(f"  α*(t=0.5)  = {spend_t05:.6f}   (hand: ≈0.005578)")
print(f"  α*(t=1.0)  = {spend_t10:.6f}   (should be 0.050000)")
print(f"  spend₁     = {incremental_spend_1:.6f}   (hand: ≈0.0056)")
print(f"  spend₂     = {incremental_spend_2:.6f}   (hand: ≈0.0444)")

# Look-1 boundary z1: Φ⁻¹(1 − spend₁)  [one-sided: reject if Z ≥ z1]
z1 = stats.norm.ppf(1.0 - incremental_spend_1)
print(f"  z1 = Φ⁻¹(1 − spend₁)   = {z1:.6f}  (hand: 2.539)")

# Look-2 boundary z2: exact solve
# Under H0 the joint distribution is bivariate normal with
# corr(Z1, Z2) = sqrt(t1/t2) = sqrt(0.5)
# P(Z1 ≥ z1 OR Z2 ≥ z2) = α = 0.05
# => 1 - P(Z1 < z1 AND Z2 < z2) = 0.05
# => P(Z1 < z1 AND Z2 < z2) = 0.95
# Bivariate normal with rho = sqrt(0.5); solve for z2 via bisect.
rho = math.sqrt(t1 / t2)   # = sqrt(0.5)

def total_alpha_given_z2(z2_candidate):
    """Return total alpha for this z2 candidate using bivariate normal."""
    # P(Z1 < z1 AND Z2 < z2) under H0 BN(0,0,1,1,rho)
    corr = [[1.0, rho], [rho, 1.0]]
    # Use upper=False (CDF), limits [z1, z2_candidate]
    p_joint_below = stats.multivariate_normal.cdf(
        [z1, z2_candidate],
        mean=[0.0, 0.0],
        cov=corr
    )
    alpha_achieved = 1.0 - p_joint_below
    return alpha_achieved - alpha_total   # target: == 0

# Search bracket — z2 must be between 1.5 and 2.5 for sure
z2_lo, z2_hi = 1.5, 2.5
fa = total_alpha_given_z2(z2_lo)
fb = total_alpha_given_z2(z2_hi)
print(f"\n  Bisect for z2: f({z2_lo:.1f})={fa:.8f}, f({z2_hi:.1f})={fb:.8f}")

z2 = brentq(total_alpha_given_z2, z2_lo, z2_hi, xtol=1e-10, rtol=1e-12, full_output=False)

# Verify achieved total alpha
corr_mat = [[1.0, rho], [rho, 1.0]]
p_joint_below_final = stats.multivariate_normal.cdf(
    [z1, z2], mean=[0.0, 0.0], cov=corr_mat
)
total_alpha_achieved = 1.0 - p_joint_below_final

print(f"  rho = sqrt(0.5)         = {rho:.6f}")
print(f"  z2 (bisect, 10-decimal) = {z2:.6f}  (hand: ≈1.687)")
print(f"  total α achieved        = {total_alpha_achieved:.6f}  (target: 0.050000)")

# ─────────────────────────────────────────────────────────────────
# STEP 3: kill_switch_threshold — exact solve
# DSR=0.95 => z_dsr = 1.644854
# (SR_pp - SR0_pp) * sqrt(T-1) / sqrt(var_term) = Φ⁻¹(0.95)
# var_term = 1 - skew*SR_pp + ((xkurt+2)/4)*SR_pp^2
# ─────────────────────────────────────────────────────────────────
SR0_pp_conf = sr0_pp          # use exact scipy value
T_holdout   = 1260
skew_anchor = 0.196
xkurt_anchor = 8.28
z_dsr_target = stats.norm.ppf(0.95)   # = 1.644854

def z_dsr_residual(sr_pp_candidate):
    var_term = (1.0
                - skew_anchor * sr_pp_candidate
                + ((xkurt_anchor + 2.0) / 4.0) * sr_pp_candidate**2)
    if var_term <= 0.0:
        return -999.0
    z_dsr_val = (sr_pp_candidate - SR0_pp_conf) * math.sqrt(T_holdout - 1) / math.sqrt(var_term)
    return z_dsr_val - z_dsr_target

# Expected solution ~ 0.08; search [0.06, 0.20]
sr_pp_lo, sr_pp_hi = 0.060, 0.200
kill_sr_pp = brentq(z_dsr_residual, sr_pp_lo, sr_pp_hi, xtol=1e-12, rtol=1e-12)
kill_sr_ann = kill_sr_pp * math.sqrt(252)

# Verify
var_term_at_kill = (1.0
                    - skew_anchor * kill_sr_pp
                    + ((xkurt_anchor + 2.0) / 4.0) * kill_sr_pp**2)
z_dsr_at_kill = (kill_sr_pp - SR0_pp_conf) * math.sqrt(T_holdout - 1) / math.sqrt(var_term_at_kill)
dsr_at_kill = stats.norm.cdf(z_dsr_at_kill)

print(f"\n[STEP 3] kill_switch_threshold (exact bisect)")
print(f"  Φ⁻¹(0.95)              = {z_dsr_target:.6f}  (sanity: 1.644854)")
print(f"  SR0_pp_conf (scipy)    = {SR0_pp_conf:.6f}  (hand: 0.034908)")
print(f"  T_holdout              = {T_holdout}")
print(f"  skew_anchor            = {skew_anchor}, xkurt_anchor = {xkurt_anchor}")
print(f"  kill SR_pp (exact)     = {kill_sr_pp:.6f}  (hand pass-1: 0.081289)")
print(f"  var_term at kill       = {var_term_at_kill:.6f}")
print(f"  z_dsr at kill          = {z_dsr_at_kill:.6f}  (target: 1.644854)")
print(f"  DSR at kill            = {dsr_at_kill:.6f}  (target: 0.950000)")
print(f"  kill_switch_threshold  = {kill_sr_ann:.6f}  (hand: 1.291)")
print(f"  kill_switch_threshold  = {kill_sr_ann:.4f}    (4-decimal)")

# ─────────────────────────────────────────────────────────────────
# STEP 4: Terminal power — single-look and joint two-look
# ─────────────────────────────────────────────────────────────────
# SR_plan = SR0_ann_conf (exact scipy) = 0.554150
# λ = SR_plan * sqrt(Y) at Y=5 years; E[Z(t)] = λ*sqrt(t)
# Under H1: Z(t) ~ N(λ*sqrt(t), 1) for each look
# Drift at look1 (t=0.5): μ1 = λ*sqrt(0.5)
# Drift at look2 (t=1.0): μ2 = λ*sqrt(1.0) = λ

SR_plan = sr0_ann                       # exact scipy value
Y = 5.0
lam = SR_plan * math.sqrt(Y)

drift_t1 = lam * math.sqrt(t1)         # = lam * sqrt(0.5)
drift_t2 = lam * math.sqrt(t2)         # = lam

# Single-look power (terminal look only, as a reference / as the Mathematician computed it)
power_single_look = stats.norm.cdf(lam - z2)

# Joint two-look power: P(Z1 >= z1 OR Z2 >= z2) under H1
# Z1 ~ N(drift_t1, 1), Z2 ~ N(drift_t2, 1), corr(Z1,Z2)=rho=sqrt(0.5)
# P(Z1 >= z1 OR Z2 >= z2) = 1 - P(Z1 < z1 AND Z2 < z2)
# Standardize: P(Z1 < z1) under H1 = Φ(z1 - drift_t1), etc.
# Bivariate: P(W1 < z1-drift_t1 AND W2 < z2-drift_t2) with W~BN(0,0,1,1,rho)
p_joint_below_h1 = stats.multivariate_normal.cdf(
    [z1 - drift_t1, z2 - drift_t2],
    mean=[0.0, 0.0],
    cov=corr_mat
)
power_two_look = 1.0 - p_joint_below_h1

print(f"\n[STEP 4] Terminal power (SR_plan = SR0_ann from scipy = {SR_plan:.6f})")
print(f"  Y = {Y} years")
print(f"  λ = SR_plan * sqrt(Y)  = {lam:.6f}")
print(f"  drift at look1 (t=0.5) = {drift_t1:.6f}")
print(f"  drift at look2 (t=1.0) = {drift_t2:.6f}")
print(f"  z1                     = {z1:.6f}")
print(f"  z2                     = {z2:.6f}")
print(f"  power single-look      = Φ(λ-z2) = Φ({lam-z2:.6f}) = {power_single_look:.6f}  (hand: ≈0.327/0.33)")
print(f"  power two-look (joint) = {power_two_look:.6f}  (hand: see below)")

# Also compute power at exact z2 using the Mathematician's approximation Φ(-0.448)
phi_minus_448 = stats.norm.cdf(-0.448174)
print(f"  Cross-check: Φ(-0.448174) = {phi_minus_448:.6f}  (hand: 0.327)")

# For completeness: also at SR_plan=0.554 (hand value, in case it differs from scipy SR0_ann)
SR_plan_hand = 0.554
lam_hand = SR_plan_hand * math.sqrt(Y)
power_single_hand = stats.norm.cdf(lam_hand - z2)
drift_t1_hand = lam_hand * math.sqrt(t1)
drift_t2_hand = lam_hand * math.sqrt(t2)
p_joint_below_h1_hand = stats.multivariate_normal.cdf(
    [z1 - drift_t1_hand, z2 - drift_t2_hand],
    mean=[0.0, 0.0], cov=corr_mat
)
power_two_look_hand = 1.0 - p_joint_below_h1_hand

print(f"\n  [At hand SR_plan=0.554 (differs by {abs(SR_plan-SR_plan_hand):.6f} ann SR)]")
print(f"  λ (hand SR_plan)       = {lam_hand:.6f}")
print(f"  power single-look      = {power_single_hand:.6f}")
print(f"  power two-look (joint) = {power_two_look_hand:.6f}")

# ─────────────────────────────────────────────────────────────────
# DIVERGENCE SUMMARY
# ─────────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("DIVERGENCE SUMMARY (hand value → scipy exact → delta → flag if >0.5%)")
print("="*70)

checks = [
    ("z_arg1 [Z⁻¹(5/6)]",         0.967422,  z_arg1),
    ("z_arg2 [Z⁻¹(1-1/6e)]",      1.542968,  z_arg2),
    ("bracket(N=6)",               1.299649,  bracket_6),
    ("SR0_ann_conf",               0.554150,  sr0_ann),
    ("SR0_pp_conf",                0.034908,  sr0_pp),
    ("ldof_spend_t05",             0.005578,  spend_t05),
    ("z1",                         2.539,     z1),
    ("z2",                         1.687,     z2),
    ("kill_switch_threshold_ann",  1.291,     kill_sr_ann),
    ("power_terminal_single_look", 0.327,     power_single_look),
    ("power_two_look_joint",       None,      power_two_look),   # no hand value given
    ("Phi_inv_0.95 sanity",        1.644854,  z_dsr_target),
]

divergences = []
for name, hand_val, exact_val in checks:
    if hand_val is None:
        print(f"  {name:40s}  exact={exact_val:.6f}  (no hand value)")
        continue
    delta = exact_val - hand_val
    pct   = abs(delta / hand_val) * 100 if hand_val != 0 else float('inf')
    flag  = " <<< DIVERGENCE >0.5%" if pct > 0.5 else ""
    print(f"  {name:40s}  hand={hand_val:10.6f}  exact={exact_val:.6f}  Δ={delta:+.6f}  ({pct:.4f}%){flag}")
    if pct > 0.5:
        divergences.append((name, hand_val, exact_val, delta, pct))

print(f"\nTotal divergences >0.5%: {len(divergences)}")

# ─────────────────────────────────────────────────────────────────
# FINAL 6-LINE FROZEN SET
# ─────────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("FINAL FROZEN SET (6-line output to report)")
print("="*70)
print(f"  bracket(N=6)              = {bracket_6:.6f}")
print(f"  SR0_ann_conf              = {sr0_ann:.6f}")
print(f"  SR0_pp_conf               = {sr0_pp:.6f}")
print(f"  z1                        = {z1:.6f}")
print(f"  z2 (bisect exact)         = {z2:.6f}")
print(f"  kill_switch_threshold_ann = {kill_sr_ann:.6f}  ({kill_sr_ann:.4f})")
print(f"  power_two_look_joint      = {power_two_look:.6f}")
print(f"  power_single_look_term    = {power_single_look:.6f}")
print(f"  total_alpha_achieved      = {total_alpha_achieved:.8f}")
print(f"  Divergences reported      = {len(divergences)}")

# Return values for YAML writing
result = {
    "z_5_6": z_arg1,
    "z_1_minus_1_over_6e": z_arg2,
    "bracket_6": bracket_6,
    "sr0_ann": sr0_ann,
    "sr0_pp": sr0_pp,
    "ldof_spend_t05": spend_t05,
    "z1": z1,
    "z2": z2,
    "total_alpha_achieved": total_alpha_achieved,
    "kill_switch_threshold_exact": kill_sr_ann,
    "power_terminal_single_look": power_single_look,
    "power_two_look_joint": power_two_look,
    "divergences": divergences,
    "lam": lam,
    "rho": rho,
    "z_dsr_target": z_dsr_target,
    "kill_sr_pp": kill_sr_pp,
    "var_term_at_kill": var_term_at_kill,
    "dsr_at_kill": dsr_at_kill,
    "drift_t1": drift_t1,
    "drift_t2": drift_t2,
    "power_two_look_at_hand_SR_plan": power_two_look_hand,
    "power_single_at_hand_SR_plan": power_single_hand,
    "SR_plan_scipy": SR_plan,
    "SR_plan_hand": SR_plan_hand,
}
print("\n[script complete — values ready for YAML artifact]")
