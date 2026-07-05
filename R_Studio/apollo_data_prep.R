# ============================================================================
# apollo_data_prep.R — long → wide pivot for Apollo (plan §7.2)
# ============================================================================
# Produces two data.frames used by the model scripts:
#   database_first    — one row per user, first choice (models M1-M3)
#   database_exploded — EXPLODE_DEPTH rows per user (ranks 1-3) with
#                       availability columns avail_1..avail_10 (model M4)
#
# Attributes are used RAW (not z-scored) to match scripts/02_estimate_models.py
# exactly, so log-likelihoods and coefficients are directly comparable.

library(dplyr)
library(tidyr)

source("apollo_config.R")

long <- read.csv(file.path(DATA_DIR, "sushi3a_choice_long.csv"))
long$alt <- long$alt_id + 1   # Apollo codes 1..10

# ---- item-level attributes (constant per item) ------------------------------
item_attrs <- long %>%
  distinct(alt, price_norm, oiliness, freq_sold) %>%
  arrange(alt)

wide_attrs <- data.frame(row.names = 1)
for (a in 1:10) {
  wide_attrs[[paste0("price_", a)]] <- item_attrs$price_norm[a]
  wide_attrs[[paste0("oil_",   a)]] <- item_attrs$oiliness[a]
  wide_attrs[[paste0("freq_",  a)]] <- item_attrs$freq_sold[a]
}

# ---- user-level info + ranks ------------------------------------------------
ranks_wide <- long %>%
  select(user_id, alt, rank) %>%
  pivot_wider(names_from = alt, values_from = rank, names_prefix = "rank_")

users <- long %>%
  distinct(user_id, gender, age_group, eastwest_current, eastwest_childhood,
           current_region, moved) %>%
  left_join(ranks_wide, by = "user_id")

# ---- first-choice database (M1-M3) ------------------------------------------
database_first <- users
database_first$choice <- apply(
  users[paste0("rank_", 1:10)], 1, function(r) which(r == 1))
database_first <- cbind(database_first,
                        wide_attrs[rep(1, nrow(database_first)), ])
for (a in 1:10) database_first[[paste0("avail_", a)]] <- 1

# ---- exploded database, ranks 1..EXPLODE_DEPTH (M4) --------------------------
explode_stage <- function(k) {
  db <- users
  db$stage  <- k
  db$choice <- apply(users[paste0("rank_", 1:10)], 1,
                     function(r) which(r == k))
  for (a in 1:10) {
    db[[paste0("avail_", a)]] <- as.integer(users[[paste0("rank_", a)]] >= k)
  }
  db
}
database_exploded <- bind_rows(lapply(1:EXPLODE_DEPTH, explode_stage)) %>%
  arrange(user_id, stage)   # panel: consecutive rows per individual
database_exploded <- cbind(database_exploded,
                           wide_attrs[rep(1, nrow(database_exploded)), ])

cat(sprintf("database_first:    %d rows\n", nrow(database_first)))
cat(sprintf("database_exploded: %d rows (%d stages)\n",
            nrow(database_exploded), EXPLODE_DEPTH))
