# ============================================================================
# 01_apollo_mnl.R — M1 (attributes), M2 (ASCs), M3 (ASCs + interactions)
# ============================================================================
# Cross-validation of scripts/02_estimate_models.py: same specifications on
# raw attributes -> LL and coefficients should match to ~1e-3.
#
# Expected Python results (2026-07-04):
#   M1 LL = -9850.73   M2 LL = -9755.07   M3 LL = -9733.21
#
# IDENTIFICATION (plan §0.3): never combine full ASCs with attribute betas —
# attributes are constant per item and perfectly collinear with the ASCs.
#
# Run from the R_Studio/ folder:
#   "C:\Program Files\R\R-4.5.3\bin\Rscript.exe" 01_apollo_mnl.R

library(apollo)
source("apollo_config.R")
source("apollo_data_prep.R")

apollo_initialise()
database <- database_first

ll_python <- c(M1 = -9850.73, M2 = -9755.07, M3 = -9733.21)
parity <- list()

# ===========================================================================
# M1 — MNL with attributes only (price, oiliness, freq_sold)
# ===========================================================================
apollo_control <- list(
  modelName       = "APOLLO_M1_attributes",
  modelDescr      = "MNL attributes only, Set A first choice",
  indivID         = "user_id",
  outputDirectory = OUT_DIR,
  panelData       = FALSE,
  seed            = SEED
)

apollo_beta  <- c(b_price = 0, b_oil = 0, b_freq = 0)
apollo_fixed <- c()

apollo_probabilities <- function(apollo_beta, apollo_inputs,
                                 functionality = "estimate") {
  apollo_attach(apollo_beta, apollo_inputs)
  on.exit(apollo_detach(apollo_beta, apollo_inputs))
  P <- list()
  V <- list()
  V[["ebi"]]        <- b_price * price_1  + b_oil * oil_1  + b_freq * freq_1
  V[["anago"]]      <- b_price * price_2  + b_oil * oil_2  + b_freq * freq_2
  V[["maguro"]]     <- b_price * price_3  + b_oil * oil_3  + b_freq * freq_3
  V[["ika"]]        <- b_price * price_4  + b_oil * oil_4  + b_freq * freq_4
  V[["uni"]]        <- b_price * price_5  + b_oil * oil_5  + b_freq * freq_5
  V[["ikura"]]      <- b_price * price_6  + b_oil * oil_6  + b_freq * freq_6
  V[["tamago"]]     <- b_price * price_7  + b_oil * oil_7  + b_freq * freq_7
  V[["toro"]]       <- b_price * price_8  + b_oil * oil_8  + b_freq * freq_8
  V[["tekka_maki"]] <- b_price * price_9  + b_oil * oil_9  + b_freq * freq_9
  V[["kappa_maki"]] <- b_price * price_10 + b_oil * oil_10 + b_freq * freq_10
  mnl_settings <- list(
    alternatives = ALT_CODES,
    avail        = 1,            # full choice set for every respondent
    choiceVar    = choice,
    utilities    = V
  )
  P[["model"]] <- apollo_mnl(mnl_settings, functionality)
  P <- apollo_prepareProb(P, apollo_inputs, functionality)
  return(P)
}

apollo_inputs <- apollo_validateInputs()
m1 <- apollo_estimate(apollo_beta, apollo_fixed,
                      apollo_probabilities, apollo_inputs)
apollo_modelOutput(m1)
apollo_saveOutput(m1)
parity[["M1"]] <- m1$maximum

# ===========================================================================
# M2 — MNL with ASCs only (reference: ebi)
# ===========================================================================
apollo_control <- list(
  modelName       = "APOLLO_M2_asc",
  modelDescr      = "MNL ASCs only, Set A first choice",
  indivID         = "user_id",
  outputDirectory = OUT_DIR,
  panelData       = FALSE,
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
    avail        = 1,
    choiceVar    = choice,
    utilities    = V
  )
  P[["model"]] <- apollo_mnl(mnl_settings, functionality)
  P <- apollo_prepareProb(P, apollo_inputs, functionality)
  return(P)
}

apollo_inputs <- apollo_validateInputs()
m2 <- apollo_estimate(apollo_beta, apollo_fixed,
                      apollo_probabilities, apollo_inputs)
apollo_modelOutput(m2)
apollo_saveOutput(m2)
parity[["M2"]] <- m2$maximum

# ===========================================================================
# M3 — MNL with ASCs + demographic interactions
# ===========================================================================
apollo_control <- list(
  modelName       = "APOLLO_M3_interactions",
  modelDescr      = "MNL ASCs + price*west, oil*age, oil*west",
  indivID         = "user_id",
  outputDirectory = OUT_DIR,
  panelData       = FALSE,
  seed            = SEED
)

apollo_beta <- c(
  asc_ebi = 0, asc_anago = 0, asc_maguro = 0, asc_ika = 0, asc_uni = 0,
  asc_ikura = 0, asc_tamago = 0, asc_toro = 0, asc_tekka_maki = 0,
  asc_kappa_maki = 0,
  b_price_x_west = 0, b_oil_x_age = 0, b_oil_x_west = 0
)
apollo_fixed <- c("asc_ebi")

apollo_probabilities <- function(apollo_beta, apollo_inputs,
                                 functionality = "estimate") {
  apollo_attach(apollo_beta, apollo_inputs)
  on.exit(apollo_detach(apollo_beta, apollo_inputs))
  P <- list()
  V <- list()
  V[["ebi"]]        <- asc_ebi        + b_price_x_west * price_1  * eastwest_current + b_oil_x_age * oil_1  * age_group + b_oil_x_west * oil_1  * eastwest_current
  V[["anago"]]      <- asc_anago      + b_price_x_west * price_2  * eastwest_current + b_oil_x_age * oil_2  * age_group + b_oil_x_west * oil_2  * eastwest_current
  V[["maguro"]]     <- asc_maguro     + b_price_x_west * price_3  * eastwest_current + b_oil_x_age * oil_3  * age_group + b_oil_x_west * oil_3  * eastwest_current
  V[["ika"]]        <- asc_ika        + b_price_x_west * price_4  * eastwest_current + b_oil_x_age * oil_4  * age_group + b_oil_x_west * oil_4  * eastwest_current
  V[["uni"]]        <- asc_uni        + b_price_x_west * price_5  * eastwest_current + b_oil_x_age * oil_5  * age_group + b_oil_x_west * oil_5  * eastwest_current
  V[["ikura"]]      <- asc_ikura      + b_price_x_west * price_6  * eastwest_current + b_oil_x_age * oil_6  * age_group + b_oil_x_west * oil_6  * eastwest_current
  V[["tamago"]]     <- asc_tamago     + b_price_x_west * price_7  * eastwest_current + b_oil_x_age * oil_7  * age_group + b_oil_x_west * oil_7  * eastwest_current
  V[["toro"]]       <- asc_toro       + b_price_x_west * price_8  * eastwest_current + b_oil_x_age * oil_8  * age_group + b_oil_x_west * oil_8  * eastwest_current
  V[["tekka_maki"]] <- asc_tekka_maki + b_price_x_west * price_9  * eastwest_current + b_oil_x_age * oil_9  * age_group + b_oil_x_west * oil_9  * eastwest_current
  V[["kappa_maki"]] <- asc_kappa_maki + b_price_x_west * price_10 * eastwest_current + b_oil_x_age * oil_10 * age_group + b_oil_x_west * oil_10 * eastwest_current
  mnl_settings <- list(
    alternatives = ALT_CODES,
    avail        = 1,
    choiceVar    = choice,
    utilities    = V
  )
  P[["model"]] <- apollo_mnl(mnl_settings, functionality)
  P <- apollo_prepareProb(P, apollo_inputs, functionality)
  return(P)
}

apollo_inputs <- apollo_validateInputs()
m3 <- apollo_estimate(apollo_beta, apollo_fixed,
                      apollo_probabilities, apollo_inputs)
apollo_modelOutput(m3)
apollo_saveOutput(m3)
parity[["M3"]] <- m3$maximum

# ===========================================================================
# LR tests along the nested chain (plan §4.0) + parity vs Python
# ===========================================================================
lr <- function(ll_r, ll_f, df) {
  stat <- 2 * (ll_f - ll_r)
  sprintf("LR = %.2f, df = %d, p = %.3g", stat, df,
          pchisq(stat, df, lower.tail = FALSE))
}
cat("\n================ NESTED CHAIN LR TESTS ================\n")
cat("M1 vs M2:", lr(m1$maximum, m2$maximum, 6), "\n")
cat("M2 vs M3:", lr(m2$maximum, m3$maximum, 3), "\n")

cat("\n================ PARITY vs PYTHON ================\n")
parity_df <- data.frame(
  model     = names(parity),
  LL_apollo = round(unlist(parity), 4),
  LL_python = ll_python[names(parity)],
  diff      = round(unlist(parity) - ll_python[names(parity)], 4)
)
print(parity_df, row.names = FALSE)
write.csv(parity_df, file.path(OUT_DIR, "apollo_crossvalidation_mnl.csv"),
          row.names = FALSE)
cat("\nSaved:", file.path(OUT_DIR, "apollo_crossvalidation_mnl.csv"), "\n")
