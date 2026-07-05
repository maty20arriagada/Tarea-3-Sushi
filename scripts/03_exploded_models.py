"""
03_exploded_models.py
=====================
Models on EXPLODED ranking data (plan §4.5): each user's ranks 1-3 become
three pseudo-choices with shrinking choice sets (10, 9, 8 alternatives).
The observed "second/third best" choices carry the substitution information
that identifies the nesting parameters with data rather than functional form.

  M2exp — MNL, ASCs only, exploded ranks 1-3          [9 params]
  M4    — Nested Logit, ASCs + 3 nest lambdas         [12 params]
          nests (config.NESTS): akami / seafood_other / non_seafood

Tests:
  - t-test lambda_m = 1 per nest (lambda = 1 -> MNL is enough in that nest)
  - LR test M2exp vs M4, chi2(3)
  - Rank-stability check: ASCs from first choice only vs ranks 1-3
    (the explosion assumes preference stability across ranking stages)

Outputs:
  outputs/tables/nested_logit_results.csv
  outputs/tables/rank_stability_check.csv

Run:  python scripts/03_exploded_models.py
"""

import numpy as np
import pandas as pd
from scipy import optimize, stats
from scipy.special import logsumexp

import config
from config import SETA_CSV, TABLES_DIR, SET_A_ORDER, NESTS

config.ensure_output_dirs()

N_ALT = 10
EXPLODE_DEPTH = 3
ASC_NAMES = [f"asc_{SET_A_ORDER[j]}" for j in range(1, N_ALT)]  # ebi = ref = 0

# nest index per alternative (alt_id order)
nest_names = list(NESTS.keys())
nest_of_alt = np.empty(N_ALT, dtype=int)
for m, (nname, members) in enumerate(NESTS.items()):
    for item in members:
        nest_of_alt[SET_A_ORDER.index(item)] = m
NEST_MASKS = np.stack([nest_of_alt == m for m in range(len(nest_names))])


# ---------------------------------------------------------------------------
# Build exploded data: ranks 1..3 -> (avail, chosen) pseudo-observations
# ---------------------------------------------------------------------------
def build_exploded(depth=EXPLODE_DEPTH):
    df = pd.read_csv(SETA_CSV).sort_values(["choice_id", "alt_id"],
                                           kind="mergesort")
    n_users = df["choice_id"].nunique()
    rank = df["rank"].to_numpy().reshape(n_users, N_ALT)     # (users, 10)

    avail_list, chosen_list, stage_list = [], [], []
    for k in range(1, depth + 1):
        avail_list.append(rank >= k)          # items not yet picked
        chosen_list.append((rank == k).argmax(axis=1))
        stage_list.append(np.full(n_users, k))
    avail = np.concatenate(avail_list)                       # (3*users, 10)
    chosen = np.concatenate(chosen_list)
    stage = np.concatenate(stage_list)
    return avail, chosen, stage, n_users


# ---------------------------------------------------------------------------
# MNL with availability (ASC-only utilities)
# ---------------------------------------------------------------------------
def mnl_negll_grad(beta, avail, chosen):
    V = np.concatenate([[0.0], beta])[None, :] * np.ones((len(chosen), 1))
    V = np.where(avail, V, -np.inf)
    denom = logsumexp(V, axis=1)
    P = np.exp(V - denom[:, None])                           # 0 where unavail
    idx = np.arange(len(chosen))
    ll = (V[idx, chosen] - denom).sum()
    # d ll / d asc_j  (j = 1..9): 1{chosen=j} - P_j
    grad = np.zeros(N_ALT - 1)
    for j in range(1, N_ALT):
        grad[j - 1] = (chosen == j).sum() - P[:, j].sum()
    return -ll, -grad


def estimate_mnl_exploded(avail, chosen, label):
    res = optimize.minimize(mnl_negll_grad, np.zeros(N_ALT - 1),
                            args=(avail, chosen), jac=True, method="BFGS",
                            options={"gtol": 1e-6})
    ll = -res.fun
    cov = numeric_cov(lambda b: mnl_negll_grad(b, avail, chosen)[0], res.x)
    print(f"  {label}: LL = {ll:,.1f}   K = {len(res.x)}")
    return {"label": label, "beta": res.x, "ll": ll, "k": len(res.x),
            "cov": cov, "n": len(chosen)}


# ---------------------------------------------------------------------------
# Nested Logit (ASC utilities; lambda_m = exp(theta_m) > 0)
# ---------------------------------------------------------------------------
def nl_negll(params, avail, chosen, free_nests=None):
    asc = np.concatenate([[0.0], params[:N_ALT - 1]])
    if free_nests is None:                                    # all lambdas free
        lam = np.exp(params[N_ALT - 1:])                      # (3,)
    else:                                                     # others fixed at 1
        lam = np.ones(len(nest_names))
        lam[free_nests] = np.exp(params[N_ALT - 1:])
    n = len(chosen)
    V = np.broadcast_to(asc, (n, N_ALT))

    S = np.empty((n, len(nest_names)))                        # logsum per nest
    for m in range(len(nest_names)):
        Vm = np.where(avail & NEST_MASKS[m], V / lam[m], -np.inf)
        S[:, m] = logsumexp(Vm, axis=1)
    IV = lam[None, :] * S                                     # lambda_m * S_m
    denom = logsumexp(IV, axis=1)

    m_i = nest_of_alt[chosen]
    idx = np.arange(n)
    S_i = S[idx, m_i]                                         # finite: chosen's nest
    ll = (V[idx, chosen] / lam[m_i] + (lam[m_i] - 1.0) * S_i - denom).sum()
    return -ll


def numeric_cov(f, x, h0=1e-5):
    """Covariance = inverse of a central-difference Hessian of the neg-LL."""
    k = len(x)
    h = h0 * (1.0 + np.abs(x))
    H = np.empty((k, k))
    f0 = f(x)
    for i in range(k):
        ei = np.zeros(k); ei[i] = h[i]
        H[i, i] = (f(x + ei) - 2 * f0 + f(x - ei)) / h[i] ** 2
        for j in range(i + 1, k):
            ej = np.zeros(k); ej[j] = h[j]
            H[i, j] = H[j, i] = (
                f(x + ei + ej) - f(x + ei - ej) - f(x - ei + ej)
                + f(x - ei - ej)) / (4 * h[i] * h[j])
    return np.linalg.inv(H)


# ===========================================================================
print(f"Building exploded data (ranks 1-{EXPLODE_DEPTH})...")
avail, chosen, stage, n_users = build_exploded()
print(f"  {n_users:,} users -> {len(chosen):,} pseudo-choices "
      f"(choice sets of 10/9/8)")

# --- M2exp: MNL benchmark on exploded data ---------------------------------
print("\nM2exp — MNL ASCs, exploded ranks 1-3")
m2exp = estimate_mnl_exploded(avail, chosen, "M2exp")

# --- M4: Nested Logit --------------------------------------------------------
def fit_nl(x0, free_nests, label):
    args = (avail, chosen, free_nests)
    res = optimize.minimize(nl_negll, x0, args=args, method="BFGS",
                            options={"gtol": 1e-5, "maxiter": 1000})
    # polish: restart once from the optimum (numeric-gradient precision loss)
    res = optimize.minimize(nl_negll, res.x, args=args, method="BFGS",
                            options={"gtol": 1e-5, "maxiter": 1000})
    print(f"  {label}: LL = {-res.fun:,.1f}   K = {len(res.x)}")
    return res


print("\nM4 — Nested Logit (nests: " + ", ".join(nest_names) + ")")
free_all = list(range(len(nest_names)))
x0 = np.concatenate([m2exp["beta"], np.zeros(len(nest_names))])  # lambda = 1
res = fit_nl(x0, free_all, "M4 (3 free lambdas)")
ll4 = -res.fun

print("  computing numerical Hessian for SEs...")
cov4 = numeric_cov(lambda p: nl_negll(p, avail, chosen, free_all), res.x)
se4 = np.sqrt(np.diag(cov4))

theta = res.x[N_ALT - 1:]
lam = np.exp(theta)
se_lam = lam * se4[N_ALT - 1:]                      # delta method
t_lam1 = (lam - 1.0) / se_lam                        # H0: lambda = 1

# M4b — if a small nest collapses to the lambda->0 boundary, re-estimate with
# that nest's lambda fixed at 1 (degenerate-nest handling, plan §10)
m4b = None
boundary = [m for m in free_all if lam[m] < 0.05]
if boundary:
    free_b = [m for m in free_all if m not in boundary]
    fixed_names = ", ".join(nest_names[m] for m in boundary)
    print(f"\nM4b — lambda at boundary in: {fixed_names} -> re-estimating "
          f"with those fixed at 1")
    x0b = np.concatenate([m2exp["beta"], np.zeros(len(free_b))])
    res_b = fit_nl(x0b, free_b, "M4b")
    cov_b = numeric_cov(lambda p: nl_negll(p, avail, chosen, free_b), res_b.x)
    se_b = np.sqrt(np.diag(cov_b))
    lam_b = np.exp(res_b.x[N_ALT - 1:])
    se_lam_b = lam_b * se_b[N_ALT - 1:]
    m4b = {"res": res_b, "ll": -res_b.fun, "free": free_b, "lam": lam_b,
           "se_lam": se_lam_b, "se": se_b}
    n_obs = len(chosen)
    bic4 = 12 * np.log(n_obs) + 2 * res.fun
    bic4b = (9 + len(free_b)) * np.log(n_obs) + 2 * res_b.fun
    print(f"  BIC M4 = {bic4:,.1f}  vs  BIC M4b = {bic4b:,.1f}  -> "
          f"{'M4b preferred' if bic4b < bic4 else 'M4 preferred'}")

# --- Tests -------------------------------------------------------------------
lr = 2 * (ll4 - m2exp["ll"])
p_lr = stats.chi2.sf(lr, len(nest_names))
print(f"\n  LR M2exp vs M4: LR = {lr:.1f}, df = {len(nest_names)}, "
      f"p = {p_lr:.2e} -> {'reject MNL' if p_lr < 0.05 else 'MNL suffices'}")
for m, nname in enumerate(nest_names):
    print(f"  lambda_{nname:14s} = {lam[m]:.3f}  (SE {se_lam[m]:.3f}, "
          f"t vs 1 = {t_lam1[m]:+.2f})")

# --- Rank-stability check: first-choice ASCs vs exploded ASCs ---------------
print("\nRank-stability check (explosion assumption, plan §10)")
avail1, chosen1 = avail[stage == 1], chosen[stage == 1]
m2_first = estimate_mnl_exploded(avail1, chosen1, "M2_first_choice")
stab = pd.DataFrame({
    "parameter": ASC_NAMES,
    "asc_first_choice": m2_first["beta"].round(4),
    "se_first_choice": np.sqrt(np.diag(m2_first["cov"])).round(4),
    "asc_exploded_1_3": m2exp["beta"].round(4),
    "se_exploded_1_3": np.sqrt(np.diag(m2exp["cov"])).round(4),
})
stab["abs_diff_in_se_units"] = (
    (stab["asc_exploded_1_3"] - stab["asc_first_choice"]).abs()
    / stab["se_first_choice"]).round(2)
max_dev = stab["abs_diff_in_se_units"].max()
print(f"  max |ASC drift| = {max_dev:.2f} first-choice SEs "
      f"({'OK' if max_dev < 2 else 'REVIEW: preferences may shift across ranks'})")

# --- Save --------------------------------------------------------------------
rows = []
for i, name in enumerate(ASC_NAMES):
    z = res.x[i] / se4[i]
    rows.append({"model": "M4", "parameter": name, "estimate": res.x[i],
                 "se": se4[i], "z_or_t": z,
                 "p_value": 2 * stats.norm.sf(abs(z)), "note": ""})
for m, nname in enumerate(nest_names):
    rows.append({"model": "M4", "parameter": f"lambda_{nname}",
                 "estimate": lam[m], "se": se_lam[m], "z_or_t": t_lam1[m],
                 "p_value": 2 * stats.norm.sf(abs(t_lam1[m])),
                 "note": "t-test vs lambda=1 (delta method on log scale)"})
if m4b is not None:
    for i, name in enumerate(ASC_NAMES):
        z = m4b["res"].x[i] / m4b["se"][i]
        rows.append({"model": "M4b", "parameter": name,
                     "estimate": m4b["res"].x[i], "se": m4b["se"][i],
                     "z_or_t": z, "p_value": 2 * stats.norm.sf(abs(z)),
                     "note": ""})
    for j, m in enumerate(m4b["free"]):
        t = (m4b["lam"][j] - 1.0) / m4b["se_lam"][j]
        rows.append({"model": "M4b", "parameter": f"lambda_{nest_names[m]}",
                     "estimate": m4b["lam"][j], "se": m4b["se_lam"][j],
                     "z_or_t": t, "p_value": 2 * stats.norm.sf(abs(t)),
                     "note": "t-test vs lambda=1"})
    for m in free_all:
        if m not in m4b["free"]:
            rows.append({"model": "M4b", "parameter": f"lambda_{nest_names[m]}",
                         "estimate": 1.0, "se": np.nan, "z_or_t": np.nan,
                         "p_value": np.nan,
                         "note": "fixed (boundary in M4: degenerate nest)"})
tab = pd.DataFrame(rows).round(5)
tab.to_csv(TABLES_DIR / "nested_logit_results.csv", index=False)
with open(TABLES_DIR / "nested_logit_results.csv", "a", encoding="utf-8") as f:
    f.write(f"\n# M4 Nested Logit, exploded ranks 1-{EXPLODE_DEPTH}, "
            f"N = {len(chosen)} pseudo-choices from {n_users} users\n"
            f"# LL(M4) = {ll4:.2f}; LL(M2exp) = {m2exp['ll']:.2f}; "
            f"LR = {lr:.2f}, df = {len(nest_names)}, p = {p_lr:.2e}\n"
            f"# lambda in (0,1): within-nest correlation; lambda = 1: MNL\n")
    if m4b is not None:
        f.write(f"# M4b: LL = {m4b['ll']:.2f}, lambdas at boundary fixed "
                f"at 1 (degenerate nest)\n")

stab.to_csv(TABLES_DIR / "rank_stability_check.csv", index=False)

print("\nDone. Tables: nested_logit_results.csv, rank_stability_check.csv")
print("Note: M5 (Mixed Logit) is optional per plan §4.6 and not estimated here.")
