"""
02_estimate_models.py
=====================
First-choice MNL models (plan §4):

  M1  — attributes only (price, oiliness, freq_sold), Set A        [3 params]
  M2  — alternative-specific constants only (ref: ebi), Set A      [9 params]
  M3  — ASCs + demographic interactions, Set A                     [12 params]
  M3r — M3 with non-significant interactions removed

Identification (plan §0.3): attributes are constant per item in Set A, so
attribute betas and a full set of ASCs are perfectly collinear and are NEVER
combined. M1 ⊂ M2 ⊂ M3 form a nested chain tested with LR tests.

Estimation: maximum likelihood, scipy BFGS with analytic gradient.
SEs: inverse of the analytic observed information matrix.

Outputs:
  outputs/tables/mnl_attributes_results.csv    (M1 + M6)
  outputs/tables/mnl_asc_results.csv           (M2 + LR test M1 vs M2)
  outputs/tables/asc_attribute_regression.csv  (descriptive OLS, plan §4.2)
  outputs/tables/interactions_results.csv      (M3, M3r + LR tests)
  outputs/tables/wtp_results.csv               (delta method, M1 & M6)
  outputs/tables/model_comparison.csv

Run:  python scripts/02_estimate_models.py
"""

import numpy as np
import pandas as pd
from scipy import optimize, stats

import config
from config import SETA_CSV, SETB_CSV, TABLES_DIR, SET_A_ORDER, REF_ALT

config.ensure_output_dirs()
np.random.seed(config.SEED)

N_ALT = 10
ATTRS = ["price_norm", "oiliness", "freq_sold"]


# ===========================================================================
# MNL core (generic over a design tensor X of shape (N, J, K))
# ===========================================================================
def mnl_negll_grad(beta, X, y):
    V = X @ beta                                    # (N, J)
    Vmax = V.max(axis=1, keepdims=True)
    expV = np.exp(V - Vmax)
    denom = expV.sum(axis=1)
    P = expV / denom[:, None]
    idx = np.arange(len(y))
    ll = (V[idx, y] - Vmax[:, 0] - np.log(denom)).sum()
    xbar = np.einsum("nj,njk->nk", P, X)
    grad = (X[idx, y] - xbar).sum(axis=0)
    return -ll, -grad


def mnl_information(beta, X):
    """Analytic observed information matrix (−Hessian of the LL)."""
    V = X @ beta
    V -= V.max(axis=1, keepdims=True)
    expV = np.exp(V)
    P = expV / expV.sum(axis=1, keepdims=True)
    xbar = np.einsum("nj,njk->nk", P, X)
    second = np.einsum("nj,njk,njl->kl", P, X, X)
    outer = np.einsum("nk,nl->kl", xbar, xbar)
    return second - outer


def check_rank(X, names, n_sample=500):
    """Guard against collinear specifications (plan §10, risk 1)."""
    sub = X[:n_sample]
    diffs = (sub - sub[:, :1, :]).reshape(-1, sub.shape[2])
    rank = np.linalg.matrix_rank(diffs)
    if rank < len(names):
        raise ValueError(
            f"Design matrix rank {rank} < {len(names)} parameters. "
            f"Collinear specification (ASCs + item-constant attributes?): {names}"
        )


def estimate_mnl(X, y, names, label):
    check_rank(X, names)
    beta0 = np.zeros(len(names))
    res = optimize.minimize(mnl_negll_grad, beta0, args=(X, y),
                            jac=True, method="BFGS",
                            options={"gtol": 1e-6, "maxiter": 500})
    if not res.success and np.abs(res.jac).max() > 1e-3:
        raise RuntimeError(f"{label} did not converge: {res.message}")
    beta = res.x
    info = mnl_information(beta, X)
    cov = np.linalg.inv(info)
    se = np.sqrt(np.diag(cov))
    ll = -res.fun
    z = beta / se
    out = pd.DataFrame({
        "model": label, "parameter": names,
        "coef": beta, "se": se, "z": z,
        "p_value": 2 * stats.norm.sf(np.abs(z)),
        "ci_low": beta - 1.96 * se, "ci_high": beta + 1.96 * se,
    })
    print(f"  {label}: LL = {ll:,.1f}   K = {len(names)}   "
          f"converged ({res.nit} iter)")
    return {"label": label, "beta": beta, "cov": cov, "ll": ll,
            "k": len(names), "n": X.shape[0], "table": out, "names": names}


def fit_stats(m, ll0):
    return {
        "model": m["label"], "n_obs": m["n"], "n_params": m["k"],
        "LL": round(m["ll"], 2),
        "rho2": round(1 - m["ll"] / ll0, 4),
        "rho2_adj": round(1 - (m["ll"] - m["k"]) / ll0, 4),
        "AIC": round(2 * m["k"] - 2 * m["ll"], 1),
        "BIC": round(m["k"] * np.log(m["n"]) - 2 * m["ll"], 1),
    }


def lr_test(m_restricted, m_full):
    lr = 2 * (m_full["ll"] - m_restricted["ll"])
    df = m_full["k"] - m_restricted["k"]
    p = stats.chi2.sf(lr, df)
    verdict = "reject H0" if p < 0.05 else "fail to reject H0"
    print(f"  LR {m_restricted['label']} vs {m_full['label']}: "
          f"LR = {lr:,.1f}, df = {df}, p = {p:.2e} -> {verdict}")
    return {"restricted": m_restricted["label"], "full": m_full["label"],
            "LR_stat": round(lr, 2), "df": df, "p_value": p,
            "conclusion": verdict}


def wtp_delta(m, price_par, attr_pars):
    """WTP_k = −β_k / β_price with delta-method SEs."""
    names = list(m["names"])
    ip = names.index(price_par)
    rows = []
    for attr in attr_pars:
        ik = names.index(attr)
        bp, bk = m["beta"][ip], m["beta"][ik]
        wtp = -bk / bp
        g = np.zeros(m["k"])
        g[ik] = -1 / bp
        g[ip] = bk / bp**2
        se = np.sqrt(g @ m["cov"] @ g)
        rows.append({"model": m["label"], "attribute": attr,
                     "wtp": round(wtp, 4), "se": round(se, 4),
                     "ci_low": round(wtp - 1.96 * se, 4),
                     "ci_high": round(wtp + 1.96 * se, 4)})
    return rows


# ===========================================================================
# Data loading — long CSV → (N, J, ·) arrays
# ===========================================================================
def load_choice_arrays(csv_path, sort_within=None):
    df = pd.read_csv(csv_path)
    if sort_within:
        df = df.sort_values(["choice_id", sort_within], kind="mergesort")
    else:
        df = df.sort_values("choice_id", kind="mergesort")
    n = df["choice_id"].nunique()
    assert len(df) == n * N_ALT, "unbalanced choice sets"
    arrays = {c: df[c].to_numpy().reshape(n, N_ALT)
              for c in df.columns if df[c].dtype != object}
    y = arrays["chosen"].argmax(axis=1)
    return df, arrays, y, n


print("Loading Set A...")
dfa, A, ya, Na = load_choice_arrays(SETA_CSV, sort_within="alt_id")
LL0_A = Na * np.log(1 / N_ALT)   # equal-shares null

# Set A stacked attribute tensor (N, 10, 3); identical across users by design
Xattr_A = np.stack([A[c] for c in ATTRS], axis=2).astype(float)

# ASC dummies: alt_id 0 (ebi) is the reference
asc_names = [f"asc_{SET_A_ORDER[j]}" for j in range(1, N_ALT)]
ASC = np.zeros((Na, N_ALT, N_ALT - 1))
for j in range(1, N_ALT):
    ASC[:, j, j - 1] = 1.0

# ===========================================================================
# M1 — attributes only (Set A)
# ===========================================================================
print("\nM1 — MNL attributes only (Set A)")
m1 = estimate_mnl(Xattr_A, ya, [f"b_{c}" for c in ATTRS], "M1_attributes")

# ===========================================================================
# M2 — ASCs only (Set A)
# ===========================================================================
print("\nM2 — MNL ASCs only (Set A)")
m2 = estimate_mnl(ASC, ya, asc_names, "M2_asc")

# Descriptive OLS of ASCs on item attributes (plan §4.2 — n = 10, no inference)
asc_full = np.concatenate([[0.0], m2["beta"]])       # ebi = 0
attr_items = Xattr_A[0]                              # (10, 3)
Xols = np.column_stack([np.ones(N_ALT), attr_items])
ols_coef, *_ = np.linalg.lstsq(Xols, asc_full, rcond=None)
resid = asc_full - Xols @ ols_coef
r2 = 1 - resid.var() / asc_full.var()
ols_tab = pd.DataFrame({
    "parameter": ["intercept"] + [f"b_{c}" for c in ATTRS],
    "coef": ols_coef.round(4),
})
ols_tab["note"] = f"descriptive OLS of 10 ASCs on item attributes; R2 = {r2:.3f}"
print(f"  ASC ~ attributes OLS (descriptive): R² = {r2:.3f}")

# ===========================================================================
# M3 — ASCs + demographic interactions (Set A)
# ===========================================================================
print("\nM3 — MNL ASCs + interactions (Set A)")
west = A["eastwest_current"][:, :1].astype(float)    # (N,1): 1 = Western Japan
age = A["age_group"][:, :1].astype(float)            # (N,1): 0-5

inter = np.stack([
    A["price_norm"] * west,      # price sensitivity gap, West vs East
    A["oiliness"] * age,         # taste for oiliness by age
    A["oiliness"] * west,        # taste for oiliness, West vs East
], axis=2).astype(float)
inter_names = ["b_price_x_west", "b_oil_x_age", "b_oil_x_west"]

X3 = np.concatenate([ASC, inter], axis=2)
m3 = estimate_mnl(X3, ya, asc_names + inter_names, "M3_interactions")

# M3r — drop interactions with |z| < 1.96, if any
t3 = m3["table"].set_index("parameter")
weak = [p for p in inter_names if abs(t3.loc[p, "z"]) < 1.96]
if weak:
    keep = [p for p in inter_names if p not in weak]
    X3r = np.concatenate(
        [ASC] + [inter[:, :, [inter_names.index(p)]] for p in keep], axis=2)
    m3r = estimate_mnl(X3r, ya, asc_names + keep, "M3r_restricted")
    print(f"  dropped (|z| < 1.96): {', '.join(weak)}")
else:
    m3r = None
    print("  all interactions significant at 5% -> no restricted variant needed")

# NOTE: the former M6 (attributes on the 100-item Set B) was removed. The
# report no longer uses Set B; scenarios and WTP now source the price/oiliness/
# freq betas directly from M1 (attributes on Set A). See 04_scenario_analysis.py.

# ===========================================================================
# LR tests along the nested chain
# ===========================================================================
print("\nLikelihood-ratio tests")
lr_rows = [lr_test(m1, m2), lr_test(m2, m3)]
if m3r is not None:
    lr_rows.append(lr_test(m3r, m3))

# ===========================================================================
# WTP (delta method) — in units of normalized price, plan §4.1 caveat
# ===========================================================================
print("\nWTP (units of normalized price)")
wtp_rows = wtp_delta(m1, "b_price_norm", ["b_oiliness", "b_freq_sold"])
wtp_tab = pd.DataFrame(wtp_rows)
print(wtp_tab.to_string(index=False))

# ===========================================================================
# Save tables
# ===========================================================================
models = [m for m in [m1, m2, m3, m3r] if m is not None]

m1["table"].round(5).to_csv(
    TABLES_DIR / "mnl_attributes_results.csv", index=False)

m2_out = m2["table"].round(5)
m2_out.to_csv(TABLES_DIR / "mnl_asc_results.csv", index=False)
with open(TABLES_DIR / "mnl_asc_results.csv", "a", encoding="utf-8") as f:
    r = lr_rows[0]
    f.write(f"\n# LR M1 vs M2: LR={r['LR_stat']} df={r['df']} "
            f"p={r['p_value']:.2e} ({r['conclusion']})\n")

ols_tab.to_csv(TABLES_DIR / "asc_attribute_regression.csv", index=False)

inter_tables = [m3["table"]] + ([m3r["table"]] if m3r is not None else [])
pd.concat(inter_tables).round(5).to_csv(
    TABLES_DIR / "interactions_results.csv", index=False)
with open(TABLES_DIR / "interactions_results.csv", "a", encoding="utf-8") as f:
    for r in lr_rows[1:]:
        f.write(f"\n# LR {r['restricted']} vs {r['full']}: LR={r['LR_stat']} "
                f"df={r['df']} p={r['p_value']:.2e} ({r['conclusion']})\n")

wtp_tab.to_csv(TABLES_DIR / "wtp_results.csv", index=False)
b_price_a = m1["beta"][list(m1["names"]).index("b_price_norm")]
if b_price_a > 0:
    with open(TABLES_DIR / "wtp_results.csv", "a", encoding="utf-8") as f:
        f.write(
            "\n# WARNING: b_price > 0 "
            f"(M1 = {b_price_a:.3f}). In this survey price acts as a quality "
            "signal (quality-price confounding): respondents rank preference, "
            "they do not pay. WTP ratios above are NOT monetary "
            "willingness-to-pay; interpret only as relative attribute "
            "trade-offs, or report marginal utilities directly.\n")
    print("  NOTE: b_price > 0 -> WTP not interpretable as monetary trade-off "
          "(annotated in wtp_results.csv)")

comparison = pd.DataFrame([fit_stats(m, LL0_A) for m in models])
comparison.to_csv(TABLES_DIR / "model_comparison.csv", index=False)
with open(TABLES_DIR / "model_comparison.csv", "a", encoding="utf-8") as f:
    f.write(f"\n# LL0 (equal shares) Set A = {LL0_A:.2f}\n")

print("\nModel comparison:")
print(comparison.to_string(index=False))

# ===========================================================================
# Sensitivity: exclude the 4 dataset authors (plan §10)
# ===========================================================================
print("\nSensitivity: re-estimating M3 without users 323/617/1431/4667...")
authors = {323, 617, 1431, 4667}
mask = ~np.isin(A["user_id"][:, 0], list(authors))
m3_sens = estimate_mnl(X3[mask], ya[mask], asc_names + inter_names,
                       "M3_no_authors")
drift = np.abs(m3_sens["beta"] - m3["beta"]).max()
print(f"  max |Δcoef| vs M3: {drift:.5f} -> "
      f"{'negligible' if drift < 0.01 else 'REVIEW'}")

print("\nEstimation complete. Tables in outputs/tables/.")
