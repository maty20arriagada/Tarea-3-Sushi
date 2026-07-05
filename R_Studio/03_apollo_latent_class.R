# ============================================================================
# 03_apollo_latent_class.R — M5-LC: Latent Class MNL (plan HW03, spec avanzada)
# ============================================================================
# Latent Class model on the exploded ranking (ranks 1-3, panel of 3
# pseudo-choices per user). Each latent class has its own full set of ASCs
# (ebi = 0 as reference within each class); class membership depends on
# observable demographics (age, East/West, gender, migration).
#
# Identification note (plan §0.3): within each class the utilities are pure
# ASCs — attributes are item-constant, so class-specific attribute betas
# would be collinear with class-specific ASCs. The LC heterogeneity is read
# from HOW the class-specific ASCs differ (e.g., a "toro-lover" class vs a
# "light-taste" class).
#
# Models: LC with S = 2 and S = 3 classes; selection by BIC against M2exp
# (S = 1). Panel grouping by user makes classes identifiable: the 3 ranks of
# one person must come from the same class.
#
# Run from the R_Studio/ folder:
#   "C:\Program Files\R\R-4.5.3\bin\Rscript.exe" 03_apollo_latent_class.R

library(apollo)
source("apollo_config.R")
source("apollo_data_prep.R")

apollo_initialise()
database <- database_exploded

N_PSEUDO <- nrow(database)
LL_M2EXP <- -29446.46   # S = 1 benchmark (validated vs Python)

results_summary <- list()

# ===========================================================================
# LC with S = 2 classes
# ===========================================================================
apollo_control <- list(
  modelName       = "APOLLO_M5_LC2",
  modelDescr      = "Latent Class MNL, 2 classes, exploded ranks 1-3",
  indivID         = "user_id",
  outputDirectory = OUT_DIR,
  panelData       = TRUE,
  seed            = SEED,
  noValidation    = FALSE
)

# Starting values: class a at the pooled (M2exp) ASCs, class b perturbed
# towards a "light taste" profile to break label symmetry.
apollo_beta <- c(
  # --- class a ASCs (ref: ebi) ---
  asc_anago_a =  0.04, asc_maguro_a =  0.23, asc_ika_a = -0.54,
  asc_uni_a   =  0.22, asc_ikura_a  =  0.16, asc_tamago_a = -0.96,
  asc_toro_a  =  1.11, asc_tekka_maki_a = -0.77, asc_kappa_maki_a = -2.07,
  # --- class b ASCs (ref: ebi) ---
  asc_anago_b =  0.04, asc_maguro_b =  0.23, asc_ika_b = -0.24,
  asc_uni_b   = -0.80, asc_ikura_b  =  0.16, asc_tamago_b =  0.04,
  asc_toro_b  =  0.11, asc_tekka_maki_b = -0.47, asc_kappa_maki_b = -1.00,
  # --- membership model (class b is the reference: V_b = 0) ---
  delta_a = 0, gamma_age_a = 0, gamma_west_a = 0, gamma_female_a = 0,
  gamma_moved_a = 0
)
apollo_fixed <- c()

apollo_lcPars <- function(apollo_beta, apollo_inputs) {
  lcpars <- list()
  V <- list()
  V[["class_a"]] <- delta_a + gamma_age_a * age_group +
    gamma_west_a * eastwest_current + gamma_female_a * gender +
    gamma_moved_a * moved
  V[["class_b"]] <- 0
  classAlloc_settings <- list(
    classes   = c(class_a = 1, class_b = 2),
    utilities = V
  )
  lcpars[["pi_values"]] <- apollo_classAlloc(classAlloc_settings)
  return(lcpars)
}

apollo_probabilities <- function(apollo_beta, apollo_inputs,
                                 functionality = "estimate") {
  apollo_attach(apollo_beta, apollo_inputs)
  on.exit(apollo_detach(apollo_beta, apollo_inputs))
  P <- list()

  avail_list <- list(ebi = avail_1, anago = avail_2, maguro = avail_3,
                     ika = avail_4, uni = avail_5, ikura = avail_6,
                     tamago = avail_7, toro = avail_8,
                     tekka_maki = avail_9, kappa_maki = avail_10)

  # ---- class a ----
  V <- list()
  V[["ebi"]]        <- 0
  V[["anago"]]      <- asc_anago_a
  V[["maguro"]]     <- asc_maguro_a
  V[["ika"]]        <- asc_ika_a
  V[["uni"]]        <- asc_uni_a
  V[["ikura"]]      <- asc_ikura_a
  V[["tamago"]]     <- asc_tamago_a
  V[["toro"]]       <- asc_toro_a
  V[["tekka_maki"]] <- asc_tekka_maki_a
  V[["kappa_maki"]] <- asc_kappa_maki_a
  mnl_settings_a <- list(alternatives = ALT_CODES, avail = avail_list,
                         choiceVar = choice, utilities = V,
                         componentName = "class_a")
  P[["class_a"]] <- apollo_mnl(mnl_settings_a, functionality)
  P[["class_a"]] <- apollo_panelProd(P[["class_a"]], apollo_inputs,
                                     functionality)

  # ---- class b ----
  V <- list()
  V[["ebi"]]        <- 0
  V[["anago"]]      <- asc_anago_b
  V[["maguro"]]     <- asc_maguro_b
  V[["ika"]]        <- asc_ika_b
  V[["uni"]]        <- asc_uni_b
  V[["ikura"]]      <- asc_ikura_b
  V[["tamago"]]     <- asc_tamago_b
  V[["toro"]]       <- asc_toro_b
  V[["tekka_maki"]] <- asc_tekka_maki_b
  V[["kappa_maki"]] <- asc_kappa_maki_b
  mnl_settings_b <- list(alternatives = ALT_CODES, avail = avail_list,
                         choiceVar = choice, utilities = V,
                         componentName = "class_b")
  P[["class_b"]] <- apollo_mnl(mnl_settings_b, functionality)
  P[["class_b"]] <- apollo_panelProd(P[["class_b"]], apollo_inputs,
                                     functionality)

  # ---- mixture ----
  lc_settings <- list(inClassProb = P, classProb = pi_values)
  P[["model"]] <- apollo_lc(lc_settings, apollo_inputs, functionality)
  P <- apollo_prepareProb(P, apollo_inputs, functionality)
  return(P)
}

apollo_inputs <- apollo_validateInputs()
lc2 <- apollo_estimate(apollo_beta, apollo_fixed,
                       apollo_probabilities, apollo_inputs)
apollo_modelOutput(lc2)
apollo_saveOutput(lc2)

k2 <- length(lc2$estimate)
results_summary[["LC2"]] <- list(model = lc2, k = k2)

# Posterior class membership (conditionals) for class profiling
cond2 <- tryCatch(
  apollo_lcConditionals(lc2, apollo_probabilities, apollo_inputs),
  error = function(e) { cat("lcConditionals failed:", conditionMessage(e),
                            "\n"); NULL }
)

# ===========================================================================
# LC with S = 3 classes
# ===========================================================================
apollo_control <- list(
  modelName       = "APOLLO_M5_LC3",
  modelDescr      = "Latent Class MNL, 3 classes, exploded ranks 1-3",
  indivID         = "user_id",
  outputDirectory = OUT_DIR,
  panelData       = TRUE,
  seed            = SEED,
  noValidation    = FALSE
)

apollo_beta <- c(
  # --- class a: pooled profile ---
  asc_anago_a =  0.04, asc_maguro_a =  0.23, asc_ika_a = -0.54,
  asc_uni_a   =  0.22, asc_ikura_a  =  0.16, asc_tamago_a = -0.96,
  asc_toro_a  =  1.11, asc_tekka_maki_a = -0.77, asc_kappa_maki_a = -2.07,
  # --- class b: light-taste profile ---
  asc_anago_b =  0.04, asc_maguro_b =  0.23, asc_ika_b = -0.24,
  asc_uni_b   = -0.80, asc_ikura_b  =  0.16, asc_tamago_b =  0.04,
  asc_toro_b  =  0.11, asc_tekka_maki_b = -0.47, asc_kappa_maki_b = -1.00,
  # --- class c: toro-fanatic profile ---
  asc_anago_c = -0.50, asc_maguro_c =  0.50, asc_ika_c = -1.00,
  asc_uni_c   =  0.70, asc_ikura_c  =  0.30, asc_tamago_c = -1.50,
  asc_toro_c  =  2.00, asc_tekka_maki_c = -0.30, asc_kappa_maki_c = -2.50,
  # --- membership (class c reference) ---
  delta_a = 0, gamma_age_a = 0, gamma_west_a = 0, gamma_female_a = 0,
  gamma_moved_a = 0,
  delta_b = 0, gamma_age_b = 0, gamma_west_b = 0, gamma_female_b = 0,
  gamma_moved_b = 0
)
apollo_fixed <- c()

apollo_lcPars <- function(apollo_beta, apollo_inputs) {
  lcpars <- list()
  V <- list()
  V[["class_a"]] <- delta_a + gamma_age_a * age_group +
    gamma_west_a * eastwest_current + gamma_female_a * gender +
    gamma_moved_a * moved
  V[["class_b"]] <- delta_b + gamma_age_b * age_group +
    gamma_west_b * eastwest_current + gamma_female_b * gender +
    gamma_moved_b * moved
  V[["class_c"]] <- 0
  classAlloc_settings <- list(
    classes   = c(class_a = 1, class_b = 2, class_c = 3),
    utilities = V
  )
  lcpars[["pi_values"]] <- apollo_classAlloc(classAlloc_settings)
  return(lcpars)
}

apollo_probabilities <- function(apollo_beta, apollo_inputs,
                                 functionality = "estimate") {
  apollo_attach(apollo_beta, apollo_inputs)
  on.exit(apollo_detach(apollo_beta, apollo_inputs))
  P <- list()

  avail_list <- list(ebi = avail_1, anago = avail_2, maguro = avail_3,
                     ika = avail_4, uni = avail_5, ikura = avail_6,
                     tamago = avail_7, toro = avail_8,
                     tekka_maki = avail_9, kappa_maki = avail_10)

  # ---- class a ----
  V <- list()
  V[["ebi"]]        <- 0
  V[["anago"]]      <- asc_anago_a
  V[["maguro"]]     <- asc_maguro_a
  V[["ika"]]        <- asc_ika_a
  V[["uni"]]        <- asc_uni_a
  V[["ikura"]]      <- asc_ikura_a
  V[["tamago"]]     <- asc_tamago_a
  V[["toro"]]       <- asc_toro_a
  V[["tekka_maki"]] <- asc_tekka_maki_a
  V[["kappa_maki"]] <- asc_kappa_maki_a
  s <- list(alternatives = ALT_CODES, avail = avail_list, choiceVar = choice,
            utilities = V, componentName = "class_a")
  P[["class_a"]] <- apollo_mnl(s, functionality)
  P[["class_a"]] <- apollo_panelProd(P[["class_a"]], apollo_inputs,
                                     functionality)

  # ---- class b ----
  V <- list()
  V[["ebi"]]        <- 0
  V[["anago"]]      <- asc_anago_b
  V[["maguro"]]     <- asc_maguro_b
  V[["ika"]]        <- asc_ika_b
  V[["uni"]]        <- asc_uni_b
  V[["ikura"]]      <- asc_ikura_b
  V[["tamago"]]     <- asc_tamago_b
  V[["toro"]]       <- asc_toro_b
  V[["tekka_maki"]] <- asc_tekka_maki_b
  V[["kappa_maki"]] <- asc_kappa_maki_b
  s <- list(alternatives = ALT_CODES, avail = avail_list, choiceVar = choice,
            utilities = V, componentName = "class_b")
  P[["class_b"]] <- apollo_mnl(s, functionality)
  P[["class_b"]] <- apollo_panelProd(P[["class_b"]], apollo_inputs,
                                     functionality)

  # ---- class c ----
  V <- list()
  V[["ebi"]]        <- 0
  V[["anago"]]      <- asc_anago_c
  V[["maguro"]]     <- asc_maguro_c
  V[["ika"]]        <- asc_ika_c
  V[["uni"]]        <- asc_uni_c
  V[["ikura"]]      <- asc_ikura_c
  V[["tamago"]]     <- asc_tamago_c
  V[["toro"]]       <- asc_toro_c
  V[["tekka_maki"]] <- asc_tekka_maki_c
  V[["kappa_maki"]] <- asc_kappa_maki_c
  s <- list(alternatives = ALT_CODES, avail = avail_list, choiceVar = choice,
            utilities = V, componentName = "class_c")
  P[["class_c"]] <- apollo_mnl(s, functionality)
  P[["class_c"]] <- apollo_panelProd(P[["class_c"]], apollo_inputs,
                                     functionality)

  # ---- mixture ----
  lc_settings <- list(inClassProb = P, classProb = pi_values)
  P[["model"]] <- apollo_lc(lc_settings, apollo_inputs, functionality)
  P <- apollo_prepareProb(P, apollo_inputs, functionality)
  return(P)
}

apollo_inputs <- apollo_validateInputs()
lc3 <- apollo_estimate(apollo_beta, apollo_fixed,
                       apollo_probabilities, apollo_inputs)
apollo_modelOutput(lc3)
apollo_saveOutput(lc3)

k3 <- length(lc3$estimate)
results_summary[["LC3"]] <- list(model = lc3, k = k3)

cond3 <- tryCatch(
  apollo_lcConditionals(lc3, apollo_probabilities, apollo_inputs),
  error = function(e) { cat("lcConditionals failed:", conditionMessage(e),
                            "\n"); NULL }
)

# ===========================================================================
# Model selection (BIC) + class profiling + export
# ===========================================================================
bic <- function(ll, k) k * log(N_PSEUDO) - 2 * ll

cat("\n================ MODEL SELECTION ================\n")
sel <- data.frame(
  model = c("M2exp (S=1)", "LC2 (S=2)", "LC3 (S=3)"),
  K     = c(9, k2, k3),
  LL    = c(LL_M2EXP, lc2$maximum, lc3$maximum),
  BIC   = c(bic(LL_M2EXP, 9), bic(lc2$maximum, k2), bic(lc3$maximum, k3))
)
sel$preferred <- ifelse(sel$BIC == min(sel$BIC), "<== BIC best", "")
print(sel, row.names = FALSE)

# ---- class profiles: posterior means of demographics by class -------------
# (robust to apollo_lcConditionals column naming; never aborts the export)
profile_classes <- function(cond, S, label) {
  if (is.null(cond)) return(NULL)
  users <- database[!duplicated(database$user_id),
                    c("user_id", "age_group", "eastwest_current", "gender",
                      "moved")]
  cond <- merge(cond, users, by.x = names(cond)[1], by.y = "user_id")
  # posterior columns = everything that is not the ID or a demographic
  wcols <- setdiff(names(cond), c(names(cond)[1], "age_group",
                                  "eastwest_current", "gender", "moved"))
  if (length(wcols) < S) return(NULL)
  out <- data.frame()
  for (s in 1:S) {
    w <- cond[[wcols[s]]]
    if (is.null(w) || length(w) != nrow(cond)) return(NULL)
    out <- rbind(out, data.frame(
      model = label, class = letters[s],
      share_pct    = round(100 * mean(w), 1),
      avg_age_grp  = round(weighted.mean(cond$age_group, w), 2),
      pct_west     = round(100 * weighted.mean(cond$eastwest_current, w), 1),
      pct_female   = round(100 * weighted.mean(cond$gender, w), 1),
      pct_moved    = round(100 * weighted.mean(cond$moved, w), 1)
    ))
  }
  out
}

prof2 <- tryCatch(profile_classes(cond2, 2, "LC2"), error = function(e) NULL)
prof3 <- tryCatch(profile_classes(cond3, 3, "LC3"), error = function(e) NULL)
cat("\n================ CLASS PROFILES (posterior) ================\n")
if (!is.null(prof2)) print(prof2, row.names = FALSE)
if (!is.null(prof3)) print(prof3, row.names = FALSE)
if (is.null(prof2) && is.null(prof3))
  cat("(conditionals not available here — run 04_lc_postprocess.R,",
      "which computes posteriors from the saved estimates)\n")

# ---- export everything -----------------------------------------------------
est_tab <- function(m, label) {
  data.frame(model = label, parameter = names(m$estimate),
             estimate = round(m$estimate, 5), se = round(m$se, 5),
             t_ratio = round(m$estimate / m$se, 3))
}
out_all <- rbind(est_tab(lc2, "LC2"), est_tab(lc3, "LC3"))
write.csv(out_all, file.path(OUT_DIR, "latent_class_results.csv"),
          row.names = FALSE)
write.csv(sel, file.path(OUT_DIR, "latent_class_selection.csv"),
          row.names = FALSE)
if (!is.null(prof2) || !is.null(prof3)) {
  write.csv(rbind(prof2, prof3),
            file.path(OUT_DIR, "latent_class_profiles.csv"),
            row.names = FALSE)
}
cat("\nSaved: latent_class_results.csv, latent_class_selection.csv,",
    "latent_class_profiles.csv\n")
