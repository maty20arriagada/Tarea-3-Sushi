"""
05_latent_class_3d.py
=====================
3D scatter that differentiates the three latent consumer classes of the
LC3 model (report §B "Segmentos latentes de consumidores").

Two things are reconstructed in Python from the Apollo LC3 estimates
(APOLLO_M5_LC3_estimates.csv), so the figure needs no R:

  1) Per-user POSTERIOR class membership (Bayes rule on the exploded panel):
        w_ns = pi_ns * L_ns / sum_s' pi_ns' * L_ns'
     where L_ns is the product of the 3 rank-stage MNL probabilities under
     class s's ASCs and pi_ns is the demographic membership logit. Each user
     is coloured by its MAP class. (Same logic as R_Studio/04_lc_postprocess.R.)

  2) Three interpretable preference axes per user, built from the observed
     ranking so the clusters separate by WHAT each class likes:
        - "Atún / akami"  : mean preference score of toro, maguro, tekka_maki
        - "Premium roe/uni": mean preference score of uni, ikura
        - "Ligero / other" : mean preference score of ebi, ika, tamago, kappa
     score_item = 10 - rank  (rank 1 = most preferred -> 9; rank 10 -> 0).

Outputs (NOT added to the report, only saved as figures):
  outputs/figures/latent_class_3d.html   (interactive, rotate/zoom)
  outputs/figures/latent_class_3d.png    (static, via kaleido)

Run:  python scripts/05_latent_class_3d.py
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import config
from config import SETA_CSV, USERS_CSV, TABLES_DIR, FIGURES_DIR, SET_A_ORDER

config.ensure_output_dirs()

ITEMS = SET_A_ORDER  # alt_id order: ebi, anago, maguro, ika, uni, ikura,
                     # tamago, toro, tekka_maki, kappa_maki
CLASS_NAMES = {
    "a": "Gourmet premium",
    "b": "Gusto ligero",
    "c": "Fanático del atún",
}
CLASS_COLORS = {"a": "#e67e22", "b": "#27ae60", "c": "#c0392b"}

# ---------------------------------------------------------------------------
# 1. Load LC3 estimates
# ---------------------------------------------------------------------------
est_df = pd.read_csv(TABLES_DIR / "APOLLO_M5_LC3_estimates.csv")
est = dict(zip(est_df.iloc[:, 0], est_df["Estimate"]))


def class_asc(s):
    """Length-10 ASC vector for class s (ebi = 0 reference), in ITEMS order."""
    return np.array([0.0] + [est[f"asc_{it}_{s}"] for it in ITEMS[1:]])


ASC = {s: class_asc(s) for s in ("a", "b", "c")}

# ---------------------------------------------------------------------------
# 2. Per-user ranking matrix + demographics
# ---------------------------------------------------------------------------
df = pd.read_csv(SETA_CSV).sort_values(["user_id", "alt_id"], kind="mergesort")
n_users = df["user_id"].nunique()
rank = df["rank"].to_numpy().reshape(n_users, 10)          # (N, 10) rank per item

users = df.drop_duplicates("user_id")[
    ["user_id", "age_group", "eastwest_current", "gender", "moved"]
].reset_index(drop=True)

# ---------------------------------------------------------------------------
# 3. In-class likelihood over the exploded ranks 1-3
# ---------------------------------------------------------------------------
def in_class_likelihood(asc):
    """L_n for every user under one class's ASCs (product over stages 1-3)."""
    expV = np.exp(asc)                                     # (10,)
    L = np.ones(n_users)
    for k in (1, 2, 3):
        avail = rank >= k                                 # items not yet picked
        chosen = (rank == k).argmax(axis=1)               # item at rank k
        denom = (avail * expV).sum(axis=1)
        L *= expV[chosen] / denom
    return L


L = np.column_stack([in_class_likelihood(ASC[s]) for s in ("a", "b", "c")])

# ---------------------------------------------------------------------------
# 4. Membership logit (class c = reference, V_c = 0) -> posteriors
# ---------------------------------------------------------------------------
def membership_V(s):
    if s == "c":
        return np.zeros(n_users)
    return (est[f"delta_{s}"]
            + est[f"gamma_age_{s}"]    * users["age_group"].to_numpy()
            + est[f"gamma_west_{s}"]   * users["eastwest_current"].to_numpy()
            + est[f"gamma_female_{s}"] * users["gender"].to_numpy()
            + est[f"gamma_moved_{s}"]  * users["moved"].to_numpy())


Vpi = np.column_stack([membership_V(s) for s in ("a", "b", "c")])
pi = np.exp(Vpi) / np.exp(Vpi).sum(axis=1, keepdims=True)

post = pi * L
post /= post.sum(axis=1, keepdims=True)                   # (N, 3) posterior
map_class = np.array(["a", "b", "c"])[post.argmax(axis=1)]

# sanity: posterior shares should match the reported profile (33.7/31.3/34.9)
shares = pd.Series(map_class).value_counts(normalize=True).reindex(
    ["a", "b", "c"]) * 100
print("MAP class shares (%):", {k: round(v, 1) for k, v in shares.items()})

# ---------------------------------------------------------------------------
# 5. Three interpretable preference axes per user (score = 10 - rank)
# ---------------------------------------------------------------------------
score = 10 - rank                                         # (N, 10), higher = liked
idx = {it: ITEMS.index(it) for it in ITEMS}

axis_tuna    = score[:, [idx["toro"], idx["maguro"], idx["tekka_maki"]]].mean(1)
axis_premium = score[:, [idx["uni"], idx["ikura"]]].mean(1)
axis_light   = score[:, [idx["ebi"], idx["ika"], idx["tamago"],
                         idx["kappa_maki"]]].mean(1)

# small jitter so the discrete lattice of ranks reads as clouds, not planes
rng = np.random.default_rng(config.SEED)
jit = lambda a: a + rng.normal(0, 0.18, size=a.shape)
X, Y, Z = jit(axis_tuna), jit(axis_premium), jit(axis_light)

# ---------------------------------------------------------------------------
# 6. Plotly 3D scatter, coloured by MAP class + class centroids
# ---------------------------------------------------------------------------
fig = go.Figure()
for s in ("a", "b", "c"):
    m = map_class == s
    fig.add_trace(go.Scatter3d(
        x=X[m], y=Y[m], z=Z[m], mode="markers",
        name=f"{CLASS_NAMES[s]} ({m.mean()*100:.1f}%)",
        marker=dict(size=2.6, color=CLASS_COLORS[s], opacity=0.55,
                    line=dict(width=0)),
        hovertemplate=(f"<b>{CLASS_NAMES[s]}</b><br>"
                       "Atún: %{x:.1f}<br>Premium: %{y:.1f}<br>"
                       "Ligero: %{z:.1f}<extra></extra>"),
    ))

# centroids (mean position of each class) as large diamonds
for s in ("a", "b", "c"):
    m = map_class == s
    fig.add_trace(go.Scatter3d(
        x=[X[m].mean()], y=[Y[m].mean()], z=[Z[m].mean()], mode="markers",
        showlegend=False,
        marker=dict(size=10, color=CLASS_COLORS[s], symbol="diamond",
                    line=dict(width=2, color="black")),
        hovertemplate=f"<b>Centroide {CLASS_NAMES[s]}</b><extra></extra>",
    ))

fig.update_layout(
    title=dict(
        text="Segmentos latentes de consumidores (LC3)<br>"
             "<sub>5.000 consumidores coloreados por clase posterior (MAP); "
             "ejes = preferencia media por grupo de sushi</sub>",
        x=0.5, xanchor="center"),
    scene=dict(
        xaxis_title="Afinidad ATÚN (toro, maguro, tekka)",
        yaxis_title="Afinidad PREMIUM (uni, ikura)",
        zaxis_title="Afinidad LIGERO (ebi, ika, tamago, kappa)",
        camera=dict(eye=dict(x=1.6, y=1.5, z=1.0)),
    ),
    legend=dict(title="Clase latente", itemsizing="constant",
                bordercolor="lightgray", borderwidth=1),
    template="plotly_white", width=1100, height=760,
)

html_path = FIGURES_DIR / "latent_class_3d.html"
png_path = FIGURES_DIR / "latent_class_3d.png"
fig.write_html(html_path, include_plotlyjs="cdn")
print(f"  [FIG] {html_path.name} (interactive)")
try:
    fig.write_image(png_path, scale=2)
    print(f"  [FIG] {png_path.name} (static, kaleido)")
except Exception as e:                                    # pragma: no cover
    print(f"  PNG export skipped ({e}); open the HTML instead.")

print("\nDone. Figures in outputs/figures/ (not embedded in the report).")
