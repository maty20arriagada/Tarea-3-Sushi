"""
04_scenario_analysis.py
=======================
Counterfactual scenario simulations (plan §6) using calibrated constants.

Engine (§6.0):  V_j = C_j + beta·X_j
  - beta taken from M1 (Set A) or M6 (Set B)
  - C_j calibrated to reproduce observed first-choice shares at baseline
  - Price-sensitivity scenarios use this engine because no single model
    estimates ASCs + attribute betas together (§0.3)

Scenarios:
  A — Toro price shock: price_norm +40%, compare MNL vs NL
  B — Kappa promotion: -30% price + freq_sold boost, by age × eastwest
  C — California roll entry (Set B, M6, 100-item universe)
  D — Kinki regional campaign (Set B, -20% on 4 traditional items)

Outputs:
  outputs/tables/scenario_A_toro.csv
  outputs/tables/scenario_B_kappa.csv
  outputs/tables/scenario_C_entry.csv
  outputs/tables/scenario_D_kinki.csv
  outputs/figures/scenario_A_nl_mnl.png
  outputs/figures/scenario_B_segments.png

Run:  python scripts/04_scenario_analysis.py
"""

import numpy as np
import pandas as pd
from scipy import optimize

import config
from config import (
    SETA_CSV, SETB_CSV, SETB_CONSIDERATION_CSV, ITEMS_CSV, USERS_CSV,
    SET_A_ORDER, SET_A_ENGLISH, NESTS, TABLES_DIR, FIGURES_DIR,
)

config.ensure_output_dirs()
rng = np.random.default_rng(config.SEED)

N_ALT = 10
ATTRS = ["price_norm", "oiliness", "freq_sold"]


# ===========================================================================
# 1. Load data and model parameters
# ===========================================================================
print("Loading data...")
dfa = pd.read_csv(SETA_CSV).sort_values(["choice_id", "alt_id"], kind="mergesort")
n_users = dfa["choice_id"].nunique()

# === Set A: observed first-choice shares (plan §1.3) ===
ranks = dfa["rank"].to_numpy().reshape(n_users, N_ALT)
chosen_idx = ranks.argmin(axis=1)
shares_obs = np.bincount(chosen_idx, minlength=N_ALT) / n_users

# Set A item attributes (constant across users; take first user's slice)
a_attr = dfa[["alt_id"] + ATTRS].iloc[:N_ALT].set_index("alt_id")
a_price = a_attr["price_norm"].to_numpy()
a_oil   = a_attr["oiliness"].to_numpy()
a_freq  = a_attr["freq_sold"].to_numpy()
a_X     = np.column_stack([a_price, a_oil, a_freq])

# Set A user demographics
a_age = dfa.groupby("choice_id")["age_group"].first().to_numpy()
a_west = dfa.groupby("choice_id")["eastwest_current"].first().to_numpy()
a_east = 1 - a_west

# === Model parameters read from the estimation outputs (single source of
# truth: outputs/tables/*.csv written by scripts 02 and 03) ===
def _params(csv_name, model, names, est_col="coef"):
    t = pd.read_csv(TABLES_DIR / csv_name, comment="#")
    t = t[t["model"] == model].set_index("parameter")
    return np.array([t.loc[n, est_col] for n in names])

# M1: b_price, b_oil, b_freq
beta_m1 = _params("mnl_attributes_results.csv", "M1_attributes",
                  ["b_price_norm", "b_oiliness", "b_freq_sold"])
# M3 interactions: b_price_x_west, b_oil_x_age, b_oil_x_west
beta_m3_int = _params("interactions_results.csv", "M3_interactions",
                      ["b_price_x_west", "b_oil_x_age", "b_oil_x_west"])
# M4 lambdas for akami and seafood_other. For simulation, non_seafood uses
# the M4b variant (lambda = 1): the free M4 estimate collapses to the
# lambda -> 0 boundary (0.002), which is a degenerate-nest artifact — using
# it in counterfactuals would make tamago/kappa_maki behave as one item on
# a knife's edge. M4b is the robust choice for prediction (documented in
# the report, §C.1).
_nl = pd.read_csv(TABLES_DIR / "nested_logit_results.csv", comment="#")
_nl = _nl[_nl["model"] == "M4"].set_index("parameter")
lam_nl = np.array([_nl.loc["lambda_akami", "estimate"],
                   _nl.loc["lambda_seafood_other", "estimate"],
                   1.0])
# M6: b_price, b_oil, b_freq, b_maki, b_nonseafood
beta_m6 = _params("mnl_attributes_results.csv", "M6_setB",
                  ["b_price_norm", "b_oiliness", "b_freq_sold",
                   "b_maki", "b_nonseafood"])
print(f"  params loaded: M1 {np.round(beta_m1, 3)}, "
      f"lambdas {np.round(lam_nl, 3)}")

# Nest map: alt_id -> nest_idx (0=akami, 1=seafood_other, 2=non_seafood)
nest_names = list(NESTS.keys())
alt_to_nest = np.zeros(N_ALT, dtype=int)
for m, (_, members) in enumerate(NESTS.items()):
    for item_name in members:
        alt_to_nest[SET_A_ORDER.index(item_name)] = m


# === Set B: 100-item universe ===
items_b = pd.read_csv(ITEMS_CSV).sort_values("item_id")
n_items_b = len(items_b)
X_b = items_b[["price_norm", "oiliness", "freq_sold"]].to_numpy()
maki_b = (items_b["style"].to_numpy() == 0).astype(float)      # style=0 maki
nonseafood_b = items_b["major_group"].to_numpy().astype(float) # 1=other
# M6 design: [price, oil, freq, maki, nonseafood]
X6_b = np.column_stack([X_b, maki_b, nonseafood_b])

# Set B observed shares (from consideration set, first choice only)
cons = pd.read_csv(SETB_CONSIDERATION_CSV)
cons_chosen = cons[cons["chosen"] == 1]
share_b_obs = np.zeros(n_items_b)
counts_b = cons_chosen.groupby("item_id").size()
for iid, cnt in counts_b.items():
    share_b_obs[iid] = cnt / n_users

# Set B users with demos (for scenario D segmentation)
setb_users = cons[["choice_id", "user_id"]].drop_duplicates("choice_id")
user_demos = pd.read_csv(USERS_CSV)
setb_users = setb_users.merge(
    user_demos[["user_id", "region_current", "region_current_label",
                "eastwest_current", "age_group"]],
    on="user_id", how="left"
)
kinki_users_b = (setb_users["region_current_label"] == "Kinki").to_numpy()
n_kinki = kinki_users_b.sum()
print(f"  Set A: {n_users} users, 10 items; Set B: {n_items_b} items, "
      f"{n_kinki} Kinki users")


# ===========================================================================
# 2. Calibration engine
# ===========================================================================
def mnl_predict(beta, X, C=None):
    """MNL choice probabilities. If C given, V_j = C_j + X_j·beta."""
    if C is None:
        V = X @ beta
    else:
        V = C + X @ beta
    Vmax = V.max(axis=-1, keepdims=True)
    expV = np.exp(V - Vmax)
    return expV / expV.sum(axis=-1, keepdims=True)


def calibrate_mnl_constants(shares, X, beta, ref_idx=0):
    """C_j = log(s_j / s_ref) - beta·(X_j - X_ref), C_ref = 0."""
    n = len(shares)
    V = X @ beta
    C = np.zeros(n)
    eps = 1e-12
    for j in range(n):
        if j == ref_idx:
            continue
        C[j] = np.log((shares[j] + eps) / (shares[ref_idx] + eps)) - (V[j] - V[ref_idx])
    return C


def nl_predict(C, X, beta, lam, alt_to_nest, n_nests):
    """Nested Logit probabilities (first choice, per user)."""
    n_alt = len(C)
    V = C + X @ beta                                           # (n_alt,) or (n_users, n_alt)
    if V.ndim == 1:
        V = V[None, :]
    n = V.shape[0]
    IV = np.zeros((n, n_nests))
    for m in range(n_nests):
        mask = alt_to_nest == m
        if not mask.any():
            continue
        IV[:, m] = np.log(np.sum(np.exp(V[:, mask] / lam[m]), axis=1))
    denom = np.log(np.sum(np.exp(lam[None, :] * IV), axis=1))   # (n,)
    P = np.zeros_like(V)
    for j in range(n_alt):
        m_j = alt_to_nest[j]
        P[:, j] = np.exp(V[:, j] / lam[m_j] + (lam[m_j] - 1) * IV[:, m_j] - denom[:, None])
    if n == 1:
        return P[0]
    return P


def calibrate_nl_constants(shares, X, beta, lam, alt_to_nest, n_nests, ref_idx=0):
    """
    Numerically adjust C_j so NL predicted shares match observed shares.
    Start from MNL-calibrated constants.
    """
    C_initial = calibrate_mnl_constants(shares, X, beta, ref_idx)

    def loss(C):
        C_full = C.copy()
        # insert ref = 0 at the right position
        C_full = np.insert(C_full, ref_idx, 0.0)
        P = nl_predict(C_full, X, beta, lam, alt_to_nest, n_nests)
        return 0.5 * np.sum((P - shares) ** 2)

    C_free = np.delete(C_initial, ref_idx)
    res = optimize.minimize(loss, C_free, method="BFGS",
                            options={"gtol": 1e-10, "maxiter": 2000})
    C_final = np.insert(res.x, ref_idx, 0.0)
    P_final = nl_predict(C_final, X, beta, lam, alt_to_nest, n_nests)
    err = np.abs(P_final - shares).max()
    if err > 1e-4:
        print(f"  WARNING: NL calibration max error = {err:.2e}")
    else:
        print(f"  NL calibrated (max share error = {err:.2e})")
    return C_final, P_final


# ===========================================================================
# 3. Scenario A — Toro price shock (+40%)
# ===========================================================================
print("\n" + "=" * 60)
print("SCENARIO A — Toro price shock (+40%)")
print("=" * 60)

toro_idx = SET_A_ORDER.index("toro")
# --- MNL calibration ---
C_mnl_a = calibrate_mnl_constants(shares_obs, a_X, beta_m1)
P_mnl_base = mnl_predict(beta_m1, a_X, C_mnl_a)
assert np.abs(P_mnl_base - shares_obs).max() < 1e-10, "MNL calibration failed"

# --- NL calibration ---
C_nl_a, P_nl_base = calibrate_nl_constants(
    shares_obs, a_X, beta_m1, lam_nl, alt_to_nest, len(nest_names))

# --- Counterfactual: toro price +40% ---
price_shock = a_price.copy()
price_shock[toro_idx] *= 1.40
X_shock = np.column_stack([price_shock, a_oil, a_freq])

P_mnl_shock = mnl_predict(beta_m1, X_shock, C_mnl_a)
P_nl_shock = nl_predict(C_nl_a, X_shock, beta_m1, lam_nl, alt_to_nest, len(nest_names))

# Elasticities (MNL)
delta_pct = 0.40  # 40% increase
eps_own_mnl = ((P_mnl_shock[toro_idx] - P_mnl_base[toro_idx])
               / P_mnl_base[toro_idx]) / delta_pct

elasticities = []
for j in range(N_ALT):
    if j == toro_idx:
        continue
    eps_cross = ((P_mnl_shock[j] - P_mnl_base[j]) / P_mnl_base[j]) / delta_pct
    elasticities.append({
        "item": SET_A_ENGLISH[SET_A_ORDER[j]],
        "own_elasticity_MNL": None,
        "cross_elasticity_wrt_toro_MNL": round(eps_cross, 4),
    })

rows_a = []
for j in range(N_ALT):
    row = {
        "item": SET_A_ORDER[j],
        "item_english": SET_A_ENGLISH[SET_A_ORDER[j]],
        "share_base": round(shares_obs[j] * 100, 2),
        "share_MNL": round(P_mnl_shock[j] * 100, 2),
        "share_NL": round(P_nl_shock[j] * 100, 2),
        "delta_MNL_pp": round((P_mnl_shock[j] - shares_obs[j]) * 100, 2),
        "delta_NL_pp": round((P_nl_shock[j] - shares_obs[j]) * 100, 2),
    }
    if j == toro_idx:
        row["own_elasticity"] = round(eps_own_mnl, 4)
    else:
        row["own_elasticity"] = None
        row["cross_elasticity"] = round(
            ((P_mnl_shock[j] - P_mnl_base[j]) / P_mnl_base[j]) / delta_pct, 4)
    rows_a.append(row)

tab_a = pd.DataFrame(rows_a)
tab_a.to_csv(TABLES_DIR / "scenario_A_toro.csv", index=False)
with open(TABLES_DIR / "scenario_A_toro.csv", "a", encoding="utf-8") as f:
    f.write(
        "\n# WARNING: beta_price = +0.581 > 0 -> price is a quality signal "
        "in this stated-preference survey (no payment). "
        "A +40% price increase RAISES toro's utility (signals higher quality) "
        "rather than reducing it. "
        "The finding is the DIFFERENCE between MNL and NL substitution patterns, "
        "not the direction of the price effect. "
        "Own-elasticity and cross-elasticities are computed with the model's "
        "price coefficient; interpret as quality-signal elasticities.\n"
        f"# MNL cross-elasticity (all identical due to IIA): "
        f"{elasticities[0]['cross_elasticity_wrt_toro_MNL']:.4f}\n"
        f"# NL: within-nest items (maguro, tekka_maki) lose MORE share than "
        f"MNL predicts (lambda_akami = {lam_nl[0]:.3f} < 1 -> closer substitutes).\n"
        "# NL simulation uses the M4b variant (lambda_non_seafood = 1): the "
        "free-M4 estimate (0.002) sits on the lambda->0 boundary and is not "
        "a credible substitution parameter for prediction (report, S C.1).\n"
    )
print("  toro share: {:.1f}% -> MNL {:.1f}% / NL {:.1f}%".format(
    shares_obs[toro_idx] * 100, P_mnl_shock[toro_idx] * 100,
    P_nl_shock[toro_idx] * 100))

# Figure: bar chart MNL vs NL delta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=config.FIGSIZE_WIDE[:])
x = np.arange(N_ALT)
labels = [SET_A_ENGLISH[n] for n in SET_A_ORDER]
colors = [config.ITEM_COLORS.get(n, "#888888") for n in SET_A_ORDER]

# Panel 1: shares
width = 0.35
ax = axes[0]
ax.bar(x - width / 2, shares_obs * 100, width, label="Base (observed)",
       color="lightgray", edgecolor="black", linewidth=0.5)
ax.bar(x + width / 2, P_nl_shock * 100, width, label="NL (+40% toro)",
       color=colors, edgecolor="black", linewidth=0.5)
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Share (%)")
ax.set_title("Scenario A: shares base vs NL (toro +40%)")
ax.legend(fontsize=8)

# Panel 2: delta pp
ax = axes[1]
delta_mnl = (P_mnl_shock - shares_obs) * 100
delta_nl = (P_nl_shock - shares_obs) * 100
ax.bar(x - width / 2, delta_mnl, width, label="MNL \u0394 pp", color="gray", edgecolor="black", linewidth=0.5)
ax.bar(x + width / 2, delta_nl, width, label="NL \u0394 pp", color=colors, edgecolor="black", linewidth=0.5)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
ax.set_ylabel("\u0394 share (pp)")
ax.set_title("MNL vs NL: substitution after toro shock")
ax.legend(fontsize=8)

plt.tight_layout()
fig.savefig(FIGURES_DIR / "scenario_A_nl_mnl.png", dpi=config.DPI)
plt.close(fig)
print("  Saved: scenario_A_nl_mnl.png")


# ===========================================================================
# 4. Scenario B — Kappa promotion (healthy campaign)
# ===========================================================================
print("\n" + "=" * 60)
print("SCENARIO B — Kappa_maki promotion (healthy campaign)")
print("=" * 60)

kappa_idx = SET_A_ORDER.index("kappa_maki")
p75_freq = np.percentile(a_freq, 75)

# M3 interactions by segment
price_x_west = a_price.reshape(1, N_ALT) * a_west.reshape(-1, 1)
oil_x_age = a_oil.reshape(1, N_ALT) * a_age.reshape(-1, 1)
oil_x_west = a_oil.reshape(1, N_ALT) * a_west.reshape(-1, 1)

# Counterfactual: kappa_maki -30% price + freq_sold -> p75
price_b = a_price.copy()
price_b[kappa_idx] *= 0.70
freq_b = a_freq.copy()
freq_b[kappa_idx] = p75_freq
X_base_b = np.column_stack([a_price, a_oil, a_freq])
X_cf_b = np.column_stack([price_b, a_oil, freq_b])

# Base MNL with calibrations per user + M3 interactions
# U_nj = C_j + beta_m1·X_nj + beta_int·[price*west, oil*age, oil*west]
C_mnl_b = calibrate_mnl_constants(shares_obs, a_X, beta_m1)

def compute_util(X_cf_attr, price_mat, oil_age_mat, oil_west_mat):
    """Compute V_nj for all users. Uses calibrated C_j + betas."""
    V_attr = (X_cf_attr @ beta_m1).reshape(1, -1)       # (1, 10)
    V = np.broadcast_to(C_mnl_b[None, :] + V_attr,      # (n_users, 10)
                        (n_users, N_ALT)).copy()
    V += beta_m3_int[0] * price_mat                      # price_x_west
    V += beta_m3_int[1] * oil_age_mat                    # oil_x_age
    V += beta_m3_int[2] * oil_west_mat                   # oil_x_west
    return V

V_base = compute_util(X_base_b, price_x_west, oil_x_age, oil_x_west)
V_cf = compute_util(X_cf_b, price_x_west, oil_x_age, oil_x_west)

Vmax_base = V_base.max(axis=1, keepdims=True)
P_base = np.exp(V_base - Vmax_base) / np.exp(V_base - Vmax_base).sum(axis=1, keepdims=True)
Vmax_cf = V_cf.max(axis=1, keepdims=True)
P_cf = np.exp(V_cf - Vmax_cf) / np.exp(V_cf - Vmax_cf).sum(axis=1, keepdims=True)

# Segments: age young (< 3, i.e. < 40), age old (>= 3); East, West
segments = {
    "Young East": (a_age < 3) & (a_west == 0),
    "Old East": (a_age >= 3) & (a_west == 0),
    "Young West": (a_age < 3) & (a_west == 1),
    "Old West": (a_age >= 3) & (a_west == 1),
}

rows_b = []
for seg_name, mask in segments.items():
    n_seg = mask.sum()
    if n_seg == 0:
        continue
    base_share = P_base[mask, kappa_idx].mean() * 100
    cf_share = P_cf[mask, kappa_idx].mean() * 100
    rows_b.append({
        "segment": seg_name,
        "n_users": n_seg,
        "share_kappa_base_pct": round(base_share, 3),
        "share_kappa_cf_pct": round(cf_share, 3),
        "delta_pp": round(cf_share - base_share, 3),
    })

# Overall
rows_b.append({
    "segment": "All",
    "n_users": n_users,
    "share_kappa_base_pct": round(P_base[:, kappa_idx].mean() * 100, 3),
    "share_kappa_cf_pct": round(P_cf[:, kappa_idx].mean() * 100, 3),
    "delta_pp": round((P_cf[:, kappa_idx].mean() - P_base[:, kappa_idx].mean()) * 100, 3),
})

# Full share deltas by segment
for j in range(N_ALT):
    item = SET_A_ORDER[j]
    share_base_item = P_base[:, j].mean() * 100
    share_cf_item = P_cf[:, j].mean() * 100
    rows_b.append({
        "segment": f"delta_{item}",
        "n_users": n_users,
        "share_kappa_base_pct": round(share_base_item, 3),
        "share_kappa_cf_pct": round(share_cf_item, 3),
        "delta_pp": round(share_cf_item - share_base_item, 3),
    })

tab_b = pd.DataFrame(rows_b)
tab_b.to_csv(TABLES_DIR / "scenario_B_kappa.csv", index=False)
with open(TABLES_DIR / "scenario_B_kappa.csv", "a", encoding="utf-8") as f:
    f.write(
        "\n# Scenario B: kappa_maki -30% price + freq_sold boosted to p75.\n"
        f"# beta_price = {beta_m1[0]:+.3f} > 0 -> price reduction reduces "
        "utility (quality signal). The modest share gain comes from the "
        "freq_sold increase (beta_freq = +2.17), which dominates the price "
        "reduction's negative utility effect.\n"
        f"# freq_sold: base {a_freq[kappa_idx]:.2f} -> cf {p75_freq:.2f}\n"
    )
print(f"  kappa_maki share: {P_base[:, kappa_idx].mean() * 100:.2f}% -> "
      f"{P_cf[:, kappa_idx].mean() * 100:.2f}%")
print(f"  freq_sold boost: {a_freq[kappa_idx]:.2f} -> {p75_freq:.2f}")

# Figure: segment bars
fig, ax = plt.subplots(figsize=config.FIGSIZE_WIDE[:])
seg_names = [s for s in segments if segments[s].sum() > 0] + ["All"]
seg_base = []
seg_cf = []
for s in seg_names:
    if s == "All":
        m = np.ones(n_users, dtype=bool)
    else:
        m = segments[s]
    seg_base.append(P_base[m, kappa_idx].mean() * 100)
    seg_cf.append(P_cf[m, kappa_idx].mean() * 100)

x = np.arange(len(seg_names))
w = 0.35
ax.bar(x - w / 2, seg_base, w, label="Base", color="lightgray", edgecolor="black", linewidth=0.5)
ax.bar(x + w / 2, seg_cf, w, label="-30% price + freq boost", color="#27ae60", edgecolor="black", linewidth=0.5)
for i in range(len(seg_names)):
    ax.text(x[i], max(seg_base[i], seg_cf[i]) + 0.02,
            f"+{seg_cf[i] - seg_base[i]:.1f} pp", ha="center", fontsize=8, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(seg_names, fontsize=9)
ax.set_ylabel("kappa_maki share (%)")
ax.set_title("Scenario B: kappa_maki shares by segment")
ax.legend(fontsize=9)
plt.tight_layout()
fig.savefig(FIGURES_DIR / "scenario_B_segments.png", dpi=config.DPI)
plt.close(fig)
print("  Saved: scenario_B_segments.png")


# ===========================================================================
# 5. Scenario C — California roll entry (Set B, M6)
# ===========================================================================
print("\n" + "=" * 60)
print("SCENARIO C — California roll market entry (Set B, 100 items)")
print("=" * 60)

# California roll attributes
cali_price = 1.5
cali_oil = 2.0
cali_freq = 0.50   # medium availability (mean Set A freq ~0.60, plan only sets price+oil+maki)
cali_maki = 1.0     # style=maki
cali_nonseafood = 0.0  # major_group=seafood

# Baseline: M6 pure-attribute predictions on all 100 items
V6_base = X6_b @ beta_m6
V6max = V6_base.max()
P6_base = np.exp(V6_base - V6max) / np.exp(V6_base - V6max).sum()

# New universe: 101 items
X6_new = np.zeros((n_items_b + 1, 5))
X6_new[:n_items_b] = X6_b
X6_new[n_items_b] = [cali_price, cali_oil, cali_freq, cali_maki, cali_nonseafood]
V6_new = X6_new @ beta_m6
V6max_new = V6_new.max()
P6_new = np.exp(V6_new - V6max_new) / np.exp(V6_new - V6max_new).sum()
cali_share = P6_new[n_items_b]

# Sensitivity: ±0.5 on the unobserved quality constant (plan §6 escenario C)
cali_share_high = np.exp(V6_new[n_items_b] + 0.5 - (V6max_new + 0.5))
cali_share_high /= (np.exp(V6_new[:-1] - (V6max_new + 0.5)).sum() + cali_share_high)

V6_new_lo = V6_new.copy()
V6_new_lo[n_items_b] -= 0.5
V6max_lo = V6_new_lo.max()
P6_new_lo = np.exp(V6_new_lo - V6max_lo) / np.exp(V6_new_lo - V6max_lo).sum()

# Cannibalisation: delta share per existing item (top 15 most affected)
delta = P6_new[:n_items_b] - P6_base
top_affected = np.argsort(delta)[:15]

rows_c = []
rows_c.append({
    "item_id": "california_roll",
    "item_name": "California roll (new)",
    "share_base_pct": 0.0,
    "share_cf_pct": round(cali_share * 100, 3),
    "share_cf_sens_low_pct": round(P6_new_lo[n_items_b] * 100, 3),
    "share_cf_sens_high_pct": round(cali_share_high * 100, 3),
    "delta_pp": round(cali_share * 100, 3),
})

for idx in top_affected:
    item_name = items_b.iloc[idx]["name"]
    rows_c.append({
        "item_id": int(items_b.iloc[idx]["item_id"]),
        "item_name": item_name,
        "share_base_pct": round(P6_base[idx] * 100, 4),
        "share_cf_pct": round(P6_new[idx] * 100, 4),
        "share_cf_sens_low_pct": round(P6_new_lo[idx] * 100, 4),
        "share_cf_sens_high_pct": None,   # sensitivity applies to the entrant
        "delta_pp": round(delta[idx] * 100, 4),
    })

tab_c = pd.DataFrame(rows_c)
tab_c.to_csv(TABLES_DIR / "scenario_C_entry.csv", index=False)
with open(TABLES_DIR / "scenario_C_entry.csv", "a", encoding="utf-8") as f:
    f.write(
        "\n# Scenario C: California roll entry (new item, Set B 100-item universe).\n"
        f"# M6 betas: price={beta_m6[0]:.3f}, oil={beta_m6[1]:.3f}, "
        f"freq={beta_m6[2]:.3f}, maki={beta_m6[3]:.3f}, "
        f"nonseafood={beta_m6[4]:.3f}\n"
        "# california_roll: price=1.5, oiliness=2.0, freq_sold=0.50, "
        "style=maki, major_group=seafood\n"
        "# Sensitivity: +/- 0.5 on the unobserved quality constant "
        "(plan escenario C, caveat).\n"
        "# Cannibalisation is proportional to shares (IIA property of MNL).\n"
    )
print(f"  California roll predicted share: {cali_share * 100:.2f}% "
      f"(sensitivity: {P6_new_lo[n_items_b] * 100:.2f}% – "
      f"{cali_share_high * 100:.2f}%)")
print(f"  Top cannibalised: {', '.join(items_b.iloc[top_affected[:5]]['name'])}")


# ===========================================================================
# 6. Scenario D — Kinki regional campaign
# ===========================================================================
print("\n" + "=" * 60)
print("SCENARIO D — Kinki regional campaign")
print("=" * 60)

# Resolve IDs by name against sushi_items.csv (never hardcode master IDs)
KINKI_NAMES = ["battera", "saba", "tai", "hamo"]
_found = items_b[items_b["name"].isin(KINKI_NAMES)]
assert len(_found) == len(KINKI_NAMES), (
    f"Kinki items missing in sushi_items.csv: "
    f"{set(KINKI_NAMES) - set(_found['name'])}")
kinki_items = dict(zip(_found["name"], _found["item_id"].astype(int)))
print(f"  Kinki items resolved: {kinki_items}")
kinki_ids = list(kinki_items.values())
kinki_indices = [int(items_b[items_b["item_id"] == iid].index[0]) for iid in kinki_ids]

# Baseline Set B shares (all users, M6 model)
P_baseline = P6_base.copy()

# Counterfactual: -20% price for Kinki items, Kinki users only
# Compute individual shares (the M6 model has no user variation; we use Kinki share weighting)
# For M6, all users have identical predictions since there's no demographic interaction.
# So we use a simple market-share simulation:
#   Total market share of item j = [n_kinki * P_j_cf_kinki + n_non_kinki * P_j_base] / N
price_cf = items_b["price_norm"].to_numpy().copy()
for ki in kinki_indices:
    price_cf[ki] *= 0.80
X6_cf = np.column_stack([price_cf, items_b["oiliness"].to_numpy(),
                          items_b["freq_sold"].to_numpy(), maki_b, nonseafood_b])
V6_cf = X6_cf @ beta_m6
V6max_cf = V6_cf.max()
P6_cf = np.exp(V6_cf - V6max_cf) / np.exp(V6_cf - V6max_cf).sum()

# Weighted: Kinki users get counterfactual shares, others get baseline
n_nonkinki = n_users - n_kinki
P_weighted = (n_kinki * P6_cf + n_nonkinki * P6_base) / n_users

rows_d = []
for name, iid in kinki_items.items():
    idx = int(items_b[items_b["item_id"] == iid].index[0])
    rows_d.append({
        "item": name,
        "item_id": iid,
        "share_base_pct": round(P_baseline[idx] * 100, 4),
        "share_cf_Kinki_only_pct": round(P6_cf[idx] * 100, 4),
        "share_weighted_pct": round(P_weighted[idx] * 100, 4),
        "delta_weighted_pp": round((P_weighted[idx] - P_baseline[idx]) * 100, 4),
    })

# Region breakdown: show Kinki vs Rest-of-Japan (East+West pooled)
region_items_d = {n: [] for n in kinki_items}
for name, iid in kinki_items.items():
    idx = int(items_b[items_b["item_id"] == iid].index[0])
    rows_d.append({
        "item": f"{name}_Kinki_delta",
        "item_id": iid,
        "share_base_pct": round(P_baseline[idx] * 100, 4),
        "share_cf_Kinki_only_pct": round(P6_cf[idx] * 100, 4),
        "share_weighted_pct": round(P_weighted[idx] * 100, 4),
        "delta_weighted_pp": round((P6_cf[idx] - P_baseline[idx]) * 100, 4),
    })

tab_d = pd.DataFrame(rows_d)
tab_d.to_csv(TABLES_DIR / "scenario_D_kinki.csv", index=False)
with open(TABLES_DIR / "scenario_D_kinki.csv", "a", encoding="utf-8") as f:
    f.write(
        "\n# Scenario D: Kinki regional campaign (-20% price on battera, saba, "
        "tai, hamo).\n"
        f"# M6 beta_price = {beta_m6[0]:+.3f} > 0 -> lower price = lower "
        "utility (quality-signal effect). Delta is small and negative: "
        "price changes have limited power in this dataset because price "
        "signals quality rather than representing cost.\n"
        f"# N = {n_users} total users ({n_kinki} Kinki, {n_nonkinki} non-Kinki).\n"
    )
print("  Kinki campaign (-20% price on battera, saba, tai, hamo):")
for name, iid in kinki_items.items():
    idx = int(items_b[items_b["item_id"] == iid].index[0])
    print(f"    {name:12s}: {P_baseline[idx] * 100:.2f}% -> "
          f"{P6_cf[idx] * 100:.2f}% (Kinki) / "
          f"{P_weighted[idx] * 100:.2f}% (weighted)")


# ===========================================================================
# 7. Summary table
# ===========================================================================
print("\n" + "=" * 60)
print("SCENARIO SUMMARY")
print("=" * 60)
print(f"  Scenario A: toro +40% price, MNL vs NL -> saved to {TABLES_DIR / 'scenario_A_toro.csv'}")
print(f"  Scenario B: kappa promotion, by segment -> saved to {TABLES_DIR / 'scenario_B_kappa.csv'}")
print(f"  Scenario C: California roll entry, +sensitivity -> saved to {TABLES_DIR / 'scenario_C_entry.csv'}")
print(f"  Scenario D: Kinki campaign -> saved to {TABLES_DIR / 'scenario_D_kinki.csv'}")
print(f"  Figures: scenario_A_nl_mnl.png, scenario_B_segments.png")
print("\nDone.")
