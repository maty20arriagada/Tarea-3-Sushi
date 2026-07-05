"""
config.py
=========
Central configuration for the HW03 sushi discrete-choice project.

Every script imports paths, alternative definitions, nests, and plotting
defaults from here so that the whole pipeline stays consistent.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
OUTPUT_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"

SETA_CSV = DATA_DIR / "sushi3a_choice_long.csv"
SETB_CSV = DATA_DIR / "sushi3b_choice_long.csv"
SETB_CONSIDERATION_CSV = DATA_DIR / "sushi3b_consideration_long.csv"
SETB_SCORE_CSV = DATA_DIR / "sushi3b_score_long.csv"
ITEMS_CSV = DATA_DIR / "sushi_items.csv"
USERS_CSV = DATA_DIR / "sushi_users.csv"


def ensure_output_dirs():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 42

# ---------------------------------------------------------------------------
# Set A alternatives
# ---------------------------------------------------------------------------
# alt_id (0-9, the alternative index used in choice models) → item name.
# item_id in the CSVs is the MASTER 100-item ID (for joins with sushi_items.csv);
# both columns are present in sushi3a_choice_long.csv. See data_dictionary.txt.
SET_A_NAMES = {
    0: "ebi", 1: "anago", 2: "maguro", 3: "ika", 4: "uni",
    5: "ikura", 6: "tamago", 7: "toro", 8: "tekka_maki", 9: "kappa_maki",
}
SET_A_ORDER = [SET_A_NAMES[i] for i in range(10)]  # alt_id order
SET_A_ENGLISH = {
    "ebi": "shrimp", "anago": "sea eel", "maguro": "tuna", "ika": "squid",
    "uni": "sea urchin", "ikura": "salmon roe", "tamago": "egg",
    "toro": "fatty tuna", "tekka_maki": "tuna roll", "kappa_maki": "cucumber roll",
}
REF_ALT = "ebi"  # reference alternative for ASC normalization

# Nests for the Nested Logit (M4), by main ingredient — see plan §4.5
NESTS = {
    "akami": ["maguro", "toro", "tekka_maki"],
    "seafood_other": ["ebi", "anago", "ika", "uni", "ikura"],
    "non_seafood": ["tamago", "kappa_maki"],
}

# ---------------------------------------------------------------------------
# Demographic labels (must match process_sushi_dataset.py)
# ---------------------------------------------------------------------------
AGE_LABELS = ["15-19", "20-29", "30-39", "40-49", "50-59", "60+"]
EASTWEST_LABELS = {0: "Eastern Japan", 1: "Western Japan"}
GENDER_LABELS = {0: "male", 1: "female"}

# Region display order (roughly north→south) for heatmaps
REGION_ORDER = [
    "Hokkaido", "Tohoku", "Hokuriku", "Kanto_Shizuoka", "Nagano_Yamanashi",
    "Chukyo", "Kinki", "Chugoku", "Shikoku", "Kyushu", "Okinawa", "Foreign",
]

# ---------------------------------------------------------------------------
# Plotting defaults
# ---------------------------------------------------------------------------
DPI = 150
FIGSIZE_WIDE = (10, 5.5)
FIGSIZE_SQUARE = (7.5, 6.5)

# One stable color per Set A item (used across all figures)
ITEM_COLORS = {
    "toro": "#c0392b", "maguro": "#e74c3c", "tekka_maki": "#f1948a",
    "uni": "#e67e22", "ikura": "#f39c12", "ebi": "#f5b7b1",
    "anago": "#8e6e53", "ika": "#95a5a6", "tamago": "#f7dc6f",
    "kappa_maki": "#27ae60",
}


def apply_plot_style():
    """Uniform matplotlib style for every figure in the project."""
    import matplotlib as mpl

    mpl.rcParams.update({
        "figure.dpi": 100,
        "savefig.dpi": DPI,
        "savefig.bbox": "tight",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linestyle": "--",
    })
