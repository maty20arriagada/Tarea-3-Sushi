# ============================================================================
# 04_lc_postprocess.R — posterior class shares & profiles for M5-LC
# ============================================================================
# Computes, WITHOUT re-estimating, the posterior class membership of each
# user from the saved Apollo estimates (APOLLO_M5_LC2/LC3_estimates.csv):
#
#   w_ns  =  pi_ns * L_ns / sum_s' pi_ns' L_ns'
#
# where pi_ns is the demographic membership logit and L_ns the product of
# the 3 exploded-rank MNL probabilities under class s. Verifies the model
# LL against Apollo's and writes:
#   latent_class_selection.csv   (S = 1/2/3, LL, BIC)
#   latent_class_profiles.csv    (share + demographic profile per class)
#   latent_class_results.csv     (all LC2/LC3 estimates, tidy)
#
# Run from the R_Studio/ folder after 03_apollo_latent_class.R.

source("apollo_config.R")
source("apollo_data_prep.R")

N_PSEUDO <- nrow(database_exploded)
LL_M2EXP <- -29446.46

read_est <- function(model_name) {
  f <- file.path(OUT_DIR, paste0(model_name, "_estimates.csv"))
  t <- read.csv(f)
  setNames(t$Estimate, t[[1]])
}

item_cols <- c("ebi", "anago", "maguro", "ika", "uni", "ikura", "tamago",
               "toro", "tekka_maki", "kappa_maki")

# per-user stage data (users x stages), choice code and availability matrix
db <- database_exploded[order(database_exploded$user_id,
                              database_exploded$stage), ]
n_users  <- length(unique(db$user_id))
stages   <- max(db$stage)
choice_m <- matrix(db$choice, nrow = n_users, byrow = TRUE)      # users x 3
avail_a  <- array(0, dim = c(n_users, stages, 10))
for (a in 1:10) {
  avail_a[, , a] <- matrix(db[[paste0("avail_", a)]], nrow = n_users,
                           byrow = TRUE)
}
users <- db[!duplicated(db$user_id),
            c("user_id", "age_group", "eastwest_current", "gender", "moved")]

class_likelihood <- function(asc) {
  # asc: length-10 utility vector (ebi = 0 first); returns L_n (users,)
  L <- rep(1, n_users)
  eV <- exp(asc)
  for (k in 1:stages) {
    denom <- as.vector(avail_a[, k, ] %*% eV)
    L <- L * eV[choice_m[, k]] / denom
  }
  L
}

posterior_lc <- function(est, S) {
  suf <- letters[1:S]
  # in-class likelihoods
  Lmat <- sapply(suf, function(s) {
    asc <- c(0, est[paste0("asc_", item_cols[-1], "_", s)])
    class_likelihood(asc)
  })                                                   # users x S
  # membership logits (last class = reference, V = 0)
  Vpi <- sapply(suf, function(s) {
    if (s == suf[S]) return(rep(0, n_users))
    est[paste0("delta_", s)] +
      est[paste0("gamma_age_", s)]    * users$age_group +
      est[paste0("gamma_west_", s)]   * users$eastwest_current +
      est[paste0("gamma_female_", s)] * users$gender +
      est[paste0("gamma_moved_", s)]  * users$moved
  })
  pi <- exp(Vpi) / rowSums(exp(Vpi))
  ll <- sum(log(rowSums(pi * Lmat)))
  w  <- (pi * Lmat) / rowSums(pi * Lmat)               # posterior
  list(ll = ll, w = w, pi = pi)
}

profile <- function(w, S, label) {
  do.call(rbind, lapply(1:S, function(s) data.frame(
    model = label, class = letters[s],
    share_pct   = round(100 * mean(w[, s]), 1),
    avg_age_grp = round(weighted.mean(users$age_group, w[, s]), 2),
    pct_west    = round(100 * weighted.mean(users$eastwest_current, w[, s]), 1),
    pct_female  = round(100 * weighted.mean(users$gender, w[, s]), 1),
    pct_moved   = round(100 * weighted.mean(users$moved, w[, s]), 1)
  )))
}

est2 <- read_est("APOLLO_M5_LC2")
est3 <- read_est("APOLLO_M5_LC3")
p2 <- posterior_lc(est2, 2)
p3 <- posterior_lc(est3, 3)

cat(sprintf("LL check LC2: manual %.2f  (Apollo: -28943.00)\n", p2$ll))
cat(sprintf("LL check LC3: manual %.2f  (Apollo: -28513.74)\n", p3$ll))

bic <- function(ll, k) k * log(N_PSEUDO) - 2 * ll
sel <- data.frame(
  model = c("M2exp (S=1)", "LC2 (S=2)", "LC3 (S=3)"),
  K     = c(9, length(est2), length(est3)),
  LL    = round(c(LL_M2EXP, p2$ll, p3$ll), 2),
  BIC   = round(c(bic(LL_M2EXP, 9), bic(p2$ll, length(est2)),
                  bic(p3$ll, length(est3))), 1)
)
sel$preferred <- ifelse(sel$BIC == min(sel$BIC), "<== BIC best", "")
print(sel, row.names = FALSE)

profs <- rbind(profile(p2$w, 2, "LC2"), profile(p3$w, 3, "LC3"))
cat("\n================ CLASS PROFILES (posterior) ================\n")
print(profs, row.names = FALSE)

tidy_est <- function(model_name, label) {
  t <- read.csv(file.path(OUT_DIR, paste0(model_name, "_estimates.csv")))
  data.frame(model = label, parameter = t[[1]],
             estimate = round(t$Estimate, 5), se = round(t$Std.err., 5),
             t_ratio = round(t$Estimate / t$Std.err., 3))
}
write.csv(rbind(tidy_est("APOLLO_M5_LC2", "LC2"),
                tidy_est("APOLLO_M5_LC3", "LC3")),
          file.path(OUT_DIR, "latent_class_results.csv"), row.names = FALSE)
write.csv(sel, file.path(OUT_DIR, "latent_class_selection.csv"),
          row.names = FALSE)
write.csv(profs, file.path(OUT_DIR, "latent_class_profiles.csv"),
          row.names = FALSE)
cat("\nSaved: latent_class_results.csv, latent_class_selection.csv,",
    "latent_class_profiles.csv\n")
