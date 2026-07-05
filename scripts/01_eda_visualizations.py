"""
01_eda_visualizations.py
========================
Exploratory data analysis for the sushi discrete-choice dataset.

Outputs (plan §5):
  outputs/figures/  — 11 PNG figures (150 dpi)
  outputs/tables/   — 5 summary CSV tables

Run:  python scripts/01_eda_visualizations.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.cluster import hierarchy

import config
from config import (
    SETA_CSV, SETB_CSV, ITEMS_CSV, USERS_CSV,
    FIGURES_DIR, TABLES_DIR,
    SET_A_ORDER, SET_A_ENGLISH, ITEM_COLORS,
    AGE_LABELS, REGION_ORDER,
    FIGSIZE_WIDE, FIGSIZE_SQUARE,
)

config.ensure_output_dirs()
config.apply_plot_style()


def item_label(name):
    return f"{name}\n({SET_A_ENGLISH[name]})"


def save(fig, filename):
    path = FIGURES_DIR / filename
    fig.savefig(path)
    plt.close(fig)
    print(f"  [FIG] {filename}")


def save_table(df, filename, **to_csv_kwargs):
    path = TABLES_DIR / filename
    df.to_csv(path, **to_csv_kwargs)
    print(f"  [TAB] {filename}")


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
print("Loading data...")
seta = pd.read_csv(SETA_CSV)
setb = pd.read_csv(SETB_CSV)
items = pd.read_csv(ITEMS_CSV)
users = pd.read_csv(USERS_CSV)

# Item-level attribute table for Set A (attributes are constant per item)
seta_items = (
    seta.groupby("item_name")[["price_norm", "oiliness", "freq_sold"]]
    .first()
    .reindex(SET_A_ORDER)
)
chosen = seta[seta["chosen"] == 1].copy()
shares = (
    chosen["item_name"].value_counts(normalize=True)
    .reindex(SET_A_ORDER)
    .rename("share")
)

# ===========================================================================
# FIGURES
# ===========================================================================
print("\nFigures:")

# --- fig01: choice shares Set A --------------------------------------------
order = shares.sort_values(ascending=False)
fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
bars = ax.bar(range(len(order)), order.values * 100,
              color=[ITEM_COLORS[n] for n in order.index])
ax.set_xticks(range(len(order)))
ax.set_xticklabels([item_label(n) for n in order.index], fontsize=8)
for i, v in enumerate(order.values * 100):
    ax.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=8)
ax.set_ylabel("Share of first choices (%)")
ax.set_title("Set A — Market share of most-preferred sushi (n = 5,000)")
save(fig, "choice_shares_setA.png")

# --- fig02: item attribute map (replaces degenerate boxplots) ---------------
fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
sizes = shares.reindex(seta_items.index).values * 4000
ax.scatter(seta_items["price_norm"], seta_items["oiliness"],
           s=sizes, c=[ITEM_COLORS[n] for n in seta_items.index],
           alpha=0.75, edgecolor="black", linewidth=0.6, zorder=3)
label_offsets = {  # avoid overlaps in the crowded low-price corner
    "tamago": (-8, 12), "tekka_maki": (10, 4), "ika": (-8, -16),
    "ebi": (12, -6), "kappa_maki": (10, 8),
}
for name, row in seta_items.iterrows():
    dx, dy = label_offsets.get(name, (8, 6))
    ax.annotate(f"{name} ({shares[name]*100:.1f}%)",
                (row["price_norm"], row["oiliness"]),
                xytext=(dx, dy), textcoords="offset points", fontsize=8,
                ha="right" if dx < 0 else "left")
ax.set_xlabel("Normalized price")
ax.set_ylabel("Oiliness (recoded: higher = more oily)")
ax.set_title("Set A — Attribute map (bubble size = first-choice share)")
ax.margins(x=0.15, y=0.12)
save(fig, "item_attribute_map.png")

# --- fig03: rank distribution heatmap ---------------------------------------
rank_pct = (
    seta.pivot_table(index="item_name", columns="rank",
                     values="user_id", aggfunc="count")
    .reindex(SET_A_ORDER) / 5000 * 100
)
mean_rank = seta.groupby("item_name")["rank"].mean().reindex(SET_A_ORDER)
row_order = mean_rank.sort_values().index
fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
im = ax.imshow(rank_pct.loc[row_order], cmap="YlOrRd", aspect="auto")
ax.set_xticks(range(10), [str(r) for r in rank_pct.columns])
ax.set_yticks(range(10), [f"{n} (mean {mean_rank[n]:.1f})" for n in row_order],
              fontsize=8)
for i, name in enumerate(row_order):
    for j in range(10):
        val = rank_pct.loc[name].iloc[j]
        ax.text(j, i, f"{val:.0f}", ha="center", va="center", fontsize=7,
                color="white" if val > 18 else "black")
ax.set_xlabel("Preference rank (1 = most preferred)")
ax.set_title("Set A — Distribution of ranks by item (% of users)")
ax.grid(False)
fig.colorbar(im, ax=ax, label="% of users", shrink=0.85)
save(fig, "rank_distribution.png")

# --- fig04: attribute correlations, Set A (10) vs all 100 items -------------
attrs = ["price_norm", "oiliness", "freq_sold"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
for ax, (df_corr, title) in zip(
    axes,
    [(seta_items[attrs], "Set A items (n = 10)"),
     (items[attrs], "All items (n = 100)")],
):
    corr = df_corr.corr()
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(3), attrs, fontsize=8)
    ax.set_yticks(range(3), attrs, fontsize=8)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center",
                    fontsize=9,
                    color="white" if abs(corr.iloc[i, j]) > 0.6 else "black")
    ax.set_title(title)
    ax.grid(False)
fig.colorbar(im, ax=axes, label="Pearson r", shrink=0.8)
fig.suptitle("Attribute correlations (price × oiliness × availability)",
             fontweight="bold")
save(fig, "attribute_correlation.png")

# --- fig05: region × preferred sushi heatmap --------------------------------
region_share = (
    pd.crosstab(chosen["current_region_label"], chosen["item_name"],
                normalize="index")
    .reindex(index=[r for r in REGION_ORDER
                    if r in chosen["current_region_label"].unique()],
             columns=SET_A_ORDER) * 100
)
fig, ax = plt.subplots(figsize=(10, 6))
im = ax.imshow(region_share, cmap="YlOrRd", aspect="auto")
ax.set_xticks(range(10), SET_A_ORDER, rotation=45, ha="right", fontsize=8)
n_users_region = chosen["current_region_label"].value_counts()
ax.set_yticks(range(len(region_share)),
              [f"{r} (n={n_users_region[r]:,})" for r in region_share.index],
              fontsize=8)
for i in range(region_share.shape[0]):
    for j in range(region_share.shape[1]):
        val = region_share.iloc[i, j]
        ax.text(j, i, f"{val:.0f}", ha="center", va="center", fontsize=7,
                color="white" if val > 25 else "black")
ax.set_title("First-choice share (%) by current region")
ax.grid(False)
fig.colorbar(im, ax=ax, label="% within region", shrink=0.85)
save(fig, "choice_by_region_heatmap.png")

# --- fig06: shares by age group and gender ----------------------------------
fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
for ax, gender in zip(axes, ["male", "female"]):
    sub = chosen[chosen["gender_label"] == gender]
    dist = (
        pd.crosstab(sub["age_label"], sub["item_name"], normalize="index")
        .reindex(index=AGE_LABELS, columns=SET_A_ORDER)
        .fillna(0) * 100
    )
    bottom = np.zeros(len(dist))
    for name in SET_A_ORDER:
        ax.bar(dist.index, dist[name], bottom=bottom,
               color=ITEM_COLORS[name], label=name, width=0.7)
        bottom += dist[name].values
    n = sub["age_label"].value_counts().reindex(AGE_LABELS).fillna(0)
    ax.set_xticks(range(len(AGE_LABELS)),
                  [f"{a}\n(n={int(n[a]):,})" for a in AGE_LABELS], fontsize=8)
    ax.set_title(gender.capitalize())
    ax.set_ylabel("Share of first choices (%)")
axes[1].legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8,
               title="Item")
fig.suptitle("First-choice composition by age group and gender",
             fontweight="bold")
save(fig, "choice_by_age_gender.png")

# --- fig07: East vs West diverging bars -------------------------------------
ew_share = (
    pd.crosstab(chosen["eastwest_current_label"], chosen["item_name"],
                normalize="index")
    .reindex(columns=SET_A_ORDER) * 100
)
diff = (ew_share.loc["Western_Japan"] - ew_share.loc["Eastern_Japan"]) \
    .sort_values()
fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
colors = ["#2980b9" if v < 0 else "#c0392b" for v in diff.values]
ax.barh(range(len(diff)), diff.values, color=colors)
ax.set_yticks(range(len(diff)), [item_label(n) for n in diff.index],
              fontsize=8)
ax.axvline(0, color="black", linewidth=0.8)
for i, v in enumerate(diff.values):
    ax.text(v + (0.08 if v >= 0 else -0.08), i, f"{v:+.1f}",
            va="center", ha="left" if v >= 0 else "right", fontsize=8)
ax.set_xlabel("Δ first-choice share (percentage points): West − East")
ax.set_title("East–West divide: which sushi over-performs in Western Japan?")
ax.margins(x=0.15)
save(fig, "eastwest_preferences.png")

# --- fig08: oiliness of chosen item by east/west and age --------------------
oil_ew = (
    chosen.groupby(["age_label", "eastwest_current_label"])["oiliness"]
    .agg(["mean", "sem"])
    .reset_index()
)
fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
for ew, color in [("Eastern_Japan", "#2980b9"), ("Western_Japan", "#c0392b")]:
    sub = oil_ew[oil_ew["eastwest_current_label"] == ew] \
        .set_index("age_label").reindex(AGE_LABELS)
    ax.errorbar(AGE_LABELS, sub["mean"], yerr=1.96 * sub["sem"],
                marker="o", capsize=3, label=ew.replace("_", " "),
                color=color)
ax.set_xlabel("Age group")
ax.set_ylabel("Mean oiliness of chosen item (± 95% CI)")
ax.set_title("Do older / Eastern consumers choose oilier sushi?")
ax.legend()
save(fig, "oiliness_by_eastwest.png")

# --- fig09: Set B chosen vs sampled attributes ------------------------------
fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
for ax, attr, label in zip(
    axes, ["price_norm", "oiliness", "freq_sold"],
    ["Normalized price", "Oiliness", "Availability (freq_sold)"],
):
    groups = [setb.loc[setb["chosen"] == 1, attr],
              setb.loc[setb["chosen"] == 0, attr]]
    t, p = stats.ttest_ind(*groups, equal_var=False)
    means = [g.mean() for g in groups]
    sems = [g.sem() for g in groups]
    ax.bar(["chosen", "sampled\n(not chosen)"], means,
           yerr=[1.96 * s for s in sems], capsize=4,
           color=["#c0392b", "#95a5a6"])
    ax.set_title(f"{label}\nΔ = {means[0]-means[1]:+.3f}  (p {'< 0.001' if p < 0.001 else f'= {p:.3f}'})",
                 fontsize=10)
fig.suptitle("Set B — Attributes of chosen vs sampled alternatives",
             fontweight="bold")
save(fig, "setB_chosen_vs_sampled.png")

# --- fig10: share of expensive items by region ------------------------------
price_median = seta_items["price_norm"].median()
chosen["expensive"] = (chosen["price_norm"] > price_median).astype(int)
exp_region = (
    chosen.groupby("current_region_label")["expensive"].agg(["mean", "count"])
    .reindex([r for r in REGION_ORDER
              if r in chosen["current_region_label"].unique()])
)
fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
ax.bar(range(len(exp_region)), exp_region["mean"] * 100, color="#8e44ad",
       alpha=0.85)
ax.axhline(chosen["expensive"].mean() * 100, color="black", linestyle="--",
           linewidth=1, label=f"National avg ({chosen['expensive'].mean()*100:.1f}%)")
ax.set_xticks(range(len(exp_region)),
              [f"{r}\n(n={int(c):,})" for r, c in
               zip(exp_region.index, exp_region["count"])],
              fontsize=7)
ax.set_ylabel("% choosing an above-median-price item")
ax.set_title(f"Premium choices by region "
             f"(items with price > {price_median:.2f}: toro, uni, ikura, anago, maguro)")
ax.legend()
save(fig, "price_sensitivity_region.png")

# --- fig11: substitution dendrogram from rank correlations ------------------
rank_matrix = seta.pivot_table(index="user_id", columns="item_name",
                               values="rank")[SET_A_ORDER]
# Spearman correlation of ranks across users; close items = ranked similarly
corr = rank_matrix.corr(method="spearman")
dist = 1 - corr
linkage = hierarchy.linkage(
    dist.values[np.triu_indices(10, k=1)], method="average")
fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
hierarchy.dendrogram(linkage, labels=corr.index.tolist(), ax=ax,
                     leaf_font_size=9, color_threshold=0.9)
ax.set_ylabel("Distance (1 − Spearman rank correlation)")
ax.set_title("Empirical similarity of items (candidate nests for the Nested Logit)")
save(fig, "substitution_dendrogram.png")

# ===========================================================================
# TABLES
# ===========================================================================
print("\nTables:")

# --- 01: choice shares -------------------------------------------------------
tab01 = pd.DataFrame({
    "count": chosen["item_name"].value_counts().reindex(SET_A_ORDER),
    "share_pct": shares * 100,
})
tab01 = tab01.sort_values("share_pct", ascending=False)
tab01["cumulative_pct"] = tab01["share_pct"].cumsum()
tab01.index.name = "item_name"
save_table(tab01.round(2), "choice_shares.csv")

# --- 02: attribute summary (one row per item — attributes are constants) ----
tab02 = seta_items.copy()
tab02.insert(0, "english", [SET_A_ENGLISH[n] for n in tab02.index])
tab02["first_choice_share_pct"] = (shares * 100).round(2)
tab02["mean_rank"] = mean_rank.round(2)
tab02.index.name = "item_name"
save_table(tab02.round(4), "attribute_summary.csv")

# --- 03: user demographics ---------------------------------------------------
rows = []
for var, label_col in [
    ("gender_label", "gender"), ("age_label", "age_group"),
    ("region_current_label", "current region"),
    ("eastwest_current_label", "east/west (current)"),
    ("moved", "moved prefecture"),
]:
    counts = users[var].value_counts()
    for value, count in counts.items():
        rows.append({"variable": label_col, "value": value,
                     "count": count, "pct": round(100 * count / len(users), 2)})
tab03 = pd.DataFrame(rows)
save_table(tab03, "user_demographics.csv", index=False)

# --- 04: rank summary, total and by east/west --------------------------------
rank_by_ew = seta.pivot_table(index="item_name",
                              columns="eastwest_current_label",
                              values="rank", aggfunc="mean")
tab04 = pd.DataFrame({
    "mean_rank": seta.groupby("item_name")["rank"].mean(),
    "median_rank": seta.groupby("item_name")["rank"].median(),
    "mean_rank_east": rank_by_ew["Eastern_Japan"],
    "mean_rank_west": rank_by_ew["Western_Japan"],
}).reindex(SET_A_ORDER)
tab04["east_west_gap"] = tab04["mean_rank_west"] - tab04["mean_rank_east"]
tab04.index.name = "item_name"
save_table(tab04.round(3), "rank_summary.csv")

# --- 05: region crosstab + chi² test -----------------------------------------
crosstab = pd.crosstab(chosen["current_region_label"], chosen["item_name"]) \
    .reindex(index=[r for r in REGION_ORDER
                    if r in chosen["current_region_label"].unique()],
             columns=SET_A_ORDER)
chi2, p, dof, _ = stats.chi2_contingency(crosstab)
crosstab.index.name = "current_region"
save_table(crosstab, "region_crosstab.csv")
with open(TABLES_DIR / "region_crosstab.csv", "a", encoding="utf-8") as f:
    f.write(f"\n# chi2 test of independence: chi2={chi2:.1f} df={dof} "
            f"p={'<0.001' if p < 0.001 else f'{p:.4f}'}\n")

print(f"\nChi² region × item: chi2={chi2:.1f}, df={dof}, p={p:.2e}")
print("\nEDA complete. Outputs in outputs/figures and outputs/tables.")
