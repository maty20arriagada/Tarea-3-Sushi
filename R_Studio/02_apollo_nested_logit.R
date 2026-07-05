# ============================================================================
# 02_apollo_nested_logit.R — M4 Nested Logit on exploded ranks 1-3 (plan §4.5)
# ============================================================================
# Cross-validation of scripts/03_exploded_models.py.
#
# Expected Python results (2026-07-04):
#   M2exp LL = -29446.5
#   M4    LL = -29112.1   lambda_akami = 0.325, lambda_seafood_other = 0.336,
#                         lambda_non_seafood -> 0 (boundary)
#   M4b   LL = -29159.7   (lambda_non_seafood fixed at 1)
#
# Data: 3 pseudo-choices per user (ranks 1-3) with shrinking availability;
# panelData = TRUE groups them by user.
#
# Run from the R_Studio/ folder:
#   "C:\Program Files\R\R-4.5.3\bin\Rscript.exe" 02_apollo_nested_logit.R

library(apollo)
source("apollo_config.R")
source("apollo_data_prep.R")

apollo_initialise()
database <- database_exploded

parity <- list()
ll_python <- c(M2exp = -29446.46, M4 = -29112.13, M4b = -29159.70)

# ===========================================================================
# M2exp — MNL benchmark on exploded data (for the LR test against M4)
# ===========================================================================
apollo_control <- list(
  modelName       = "APOLLO_M2exp_mnl_exploded",
  modelDescr      = "MNL ASCs, exploded ranks 1-3",
  indivID         = "user_id",
  outputDirectory = OUT_DIR,
  panelData       = TRUE,
  seed            = SEED
)

apollo_beta <- c(
  asc_ebi = 0, asc_anago = 0, asc_maguro = 0, asc_ika = 0, asc_uni = 0,
  asc_ikura = 0, asc_tamago = 0, asc_toro = 0, asc_tekka_maki = 0,
  asc_kappa_maki = 0
)
apollo_fixed <- c("asc_ebi")

apollo_probabilities <- function(apollo_beta, apollo_inputs,
                                 functionality = "estimate") {
  apollo_attach(apollo_beta, apollo_inputs)
  on.exit(apollo_detach(apollo_beta, apollo_inputs))
  P <- list()
  V <- list()
  V[["ebi"]]        <- asc_ebi
  V[["anago"]]      <- asc_anago
  V[["maguro"]]     <- asc_maguro
  V[["ika"]]        <- asc_ika
  V[["uni"]]        <- asc_uni
  V[["ikura"]]      <- asc_ikura
  V[["tamago"]]     <- asc_tamago
  V[["toro"]]       <- asc_toro
  V[["tekka_maki"]] <- asc_tekka_maki
  V[["kappa_maki"]] <- asc_kappa_maki
  mnl_settings <- list(
    alternatives = ALT_CODES,
    avail        = list(ebi = avail_1, anago = avail_2, maguro = avail_3,
                        ika = avail_4, uni = avail_5, ikura = avail_6,
                        tamago = avail_7, toro = avail_8,
                        tekka_maki = avail_9, kappa_maki = avail_10),
    choiceVar    = choice,
    utilities    = V
  )
  P[["model"]] <- apollo_mnl(mnl_settings, functionality)
  P <- apollo_panelProd(P, apollo_inputs, functionality)
  P <- apollo_prepareProb(P, apollo_inputs, functionality)
  return(P)
}

apollo_inputs <- apollo_validateInputs()
m2exp <- apollo_estimate(apollo_beta, apollo_fixed,
                         apollo_probabilities, apollo_inputs)
apollo_modelOutput(m2exp)
apollo_saveOutput(m2exp)
parity[["M2exp"]] <- m2exp$maximum

# ===========================================================================
# M4b — Nested Logit with lambda_non_seafood FIXED at 1 (degenerate nest)
# ===========================================================================
# NOTE ON THE FREE M4: with all three lambdas free, lambda_non_seafood
# collapses to the lambda -> 0 boundary (Python estimate: 0.002). At that
# boundary V/lambda overflows and Apollo's BGW optimiser returns NaN — the
# unrestricted M4 is therefore estimated only in Python (which uses an
# exponential reparameterisation + logsumexp guard; see
# scripts/03_exploded_models.py). Apollo cross-validates M2exp and M4b.
apollo_control <- list(
  modelName       = "APOLLO_M4b_nl_fixed_lambda",
  modelDescr      = "NL with lambda_non_seafood = 1 (degenerate nest)",
  indivID         = "user_id",
  outputDirectory = OUT_DIR,
  panelData       = TRUE,
  seed            = SEED
)

apollo_beta <- c(
  asc_ebi = 0, asc_anago = 0, asc_maguro = 0, asc_ika = 0, asc_uni = 0,
  asc_ikura = 0, asc_tamago = 0, asc_toro = 0, asc_tekka_maki = 0,
  asc_kappa_maki = 0,
  lambda_akami = 0.5, lambda_seafood_other = 0.5, lambda_non_seafood = 1
)
apollo_fixed <- c("asc_ebi", "lambda_non_seafood")

apollo_probabilities <- function(apollo_beta, apollo_inputs,
                                 functionality = "estimate") {
  apollo_attach(apollo_beta, apollo_inputs)
  on.exit(apollo_detach(apollo_beta, apollo_inputs))
  P <- list()
  V <- list()
  V[["ebi"]]        <- asc_ebi
  V[["anago"]]      <- asc_anago
  V[["maguro"]]     <- asc_maguro
  V[["ika"]]        <- asc_ika
  V[["uni"]]        <- asc_uni
  V[["ikura"]]      <- asc_ikura
  V[["tamago"]]     <- asc_tamago
  V[["toro"]]       <- asc_toro
  V[["tekka_maki"]] <- asc_tekka_maki
  V[["kappa_maki"]] <- asc_kappa_maki
  nlNests <- list(root = 1,
                  akami = lambda_akami,
                  seafood_other = lambda_seafood_other,
                  non_seafood = lambda_non_seafood)
  nlStructure <- list(
    root          = c("akami", "seafood_other", "non_seafood"),
    akami         = c("maguro", "toro", "tekka_maki"),
    seafood_other = c("ebi", "anago", "ika", "uni", "ikura"),
    non_seafood   = c("tamago", "kappa_maki")
  )
  nl_settings <- list(
    alternatives = ALT_CODES,
    avail        = list(ebi = avail_1, anago = avail_2, maguro = avail_3,
                        ika = avail_4, uni = avail_5, ikura = avail_6,
                        tamago = avail_7, toro = avail_8,
                        tekka_maki = avail_9, kappa_maki = avail_10),
    choiceVar    = choice,
    utilities    = V,
    nlNests      = nlNests,
    nlStructure  = nlStructure
  )
  P[["model"]] <- apollo_nl(nl_settings, functionality)
  P <- apollo_panelProd(P, apollo_inputs, functionality)
  P <- apollo_prepareProb(P, apollo_inputs, functionality)
  return(P)
}

apollo_inputs <- apollo_validateInputs()
m4b <- apollo_estimate(apollo_beta, apollo_fixed,
                       apollo_probabilities, apollo_inputs)
apollo_modelOutput(m4b)
apollo_saveOutput(m4b)
parity[["M4b"]] <- m4b$maximum

# ===========================================================================
# Tests + parity vs Python
# ===========================================================================
cat("\n================ TESTS ================\n")
lr_stat <- 2 * (m4b$maximum - m2exp$maximum)
cat(sprintf("LR M2exp vs M4b: %.1f, df = 2, p = %.3g\n",
            lr_stat, pchisq(lr_stat, 2, lower.tail = FALSE)))
for (lam in c("lambda_akami", "lambda_seafood_other")) {
  est <- m4b$estimate[lam]; se <- m4b$se[lam]
  cat(sprintf("%-22s = %.4f  (SE %.4f, t vs 1 = %+.2f)\n",
              lam, est, se, (est - 1) / se))
}
cat("lambda_non_seafood     = 1 (fixed; free estimate hits the",
    "lambda -> 0 boundary, see header note)\n")

cat("\n================ PARITY vs PYTHON ================\n")
parity_df <- data.frame(
  model     = names(parity),
  LL_apollo = round(unlist(parity), 4),
  LL_python = ll_python[names(parity)],
  diff      = round(unlist(parity) - ll_python[names(parity)], 4)
)
print(parity_df, row.names = FALSE)
write.csv(parity_df, file.path(OUT_DIR, "apollo_crossvalidation_nl.csv"),
          row.names = FALSE)
cat("\nSaved:", file.path(OUT_DIR, "apollo_crossvalidation_nl.csv"), "\n")
