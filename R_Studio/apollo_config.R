# ============================================================================
# apollo_config.R — Sushi Set A, Apollo configuration (plan §7.1)
# ============================================================================
# Alternative codes are alt_id + 1 (Apollo requires 1-based codes).

SUSHI_ITEMS_A <- c("ebi", "anago", "maguro", "ika", "uni",
                   "ikura", "tamago", "toro", "tekka_maki", "kappa_maki")
ALT_CODES <- setNames(1:10, SUSHI_ITEMS_A)
REF_ALT   <- "ebi"   # asc_ebi = 0

# Nests by main ingredient (plan §4.5; validated by the EDA dendrogram)
NEST_MAP <- list(
  akami         = c(3, 8, 9),          # maguro, toro, tekka_maki
  seafood_other = c(1, 2, 4, 5, 6),    # ebi, anago, ika, uni, ikura
  non_seafood   = c(7, 10)             # tamago, kappa_maki
)

SEED <- 42
EXPLODE_DEPTH <- 3   # ranks 1-3 for exploded models (M4, LC)

# Working-directory contract: run the model scripts FROM the R_Studio/ folder
# (Rscript from a terminal, or setwd() in RStudio). BASE_DIR is its parent.
BASE_DIR <- normalizePath(file.path(getwd(), ".."))
DATA_DIR <- file.path(BASE_DIR, "Data")
OUT_DIR  <- file.path(BASE_DIR, "outputs", "tables")

if (!file.exists(file.path(DATA_DIR, "sushi3a_choice_long.csv"))) {
  stop("Data/sushi3a_choice_long.csv not found. Set the working directory to ",
       "the R_Studio/ folder before sourcing (current: ", getwd(), ")")
}
dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)
