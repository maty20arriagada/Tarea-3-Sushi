"""
process_sushi_dataset.py
=========================
Transforms the SUSHI Preference Data Sets (Kamishima, 2003)
into discrete-choice long-format CSV files for HW02/HW03.

Input  — data/sushi_raw/* (9 raw files from https://www.kamishima.net/sushi/)
Output — data/sushi_items.csv
         data/sushi_users.csv
         data/sushi3a_choice_long.csv
         data/sushi3b_choice_long.csv
         data/sushi3b_consideration_long.csv
         data/sushi3b_score_long.csv
         data/data_dictionary.txt

Reproduce : python scripts/process_sushi_dataset.py
"""

import os
import csv
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# 0.  Paths & constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "sushi_raw"
SEED = 42
N_ALTERNATIVES_SAMPLE = 9  # sampled non‑chosen alternatives for set B

random.seed(SEED)

# ---------------------------------------------------------------------------
# 0a. Set A ID → master item ID mapping
# ---------------------------------------------------------------------------
# The file sushi3a.5000.10.order uses its OWN item numbering (0-9), defined
# in README-en.txt ("ID for the item set A"), which does NOT coincide with
# the master 100-item numbering of sushi3.idata for IDs 5-9:
#
#   Set A ID   name         master ID (sushi3.idata row)
#   0          ebi          0
#   1          anago        1
#   2          maguro       2
#   3          ika          3
#   4          uni          4
#   5          ikura        6    (master 5 = tako  — NOT in Set A)
#   6          tamago       7    (master 6 = ikura)
#   7          toro         8    (master 7 = tamago)
#   8          tekka_maki   26   (master 8 = toro)
#   9          kappa_maki   29   (master 9 = amaebi — NOT in Set A)
#
# Joining Set A responses directly against sushi3.idata therefore mislabels
# half the choice set. This map fixes the join.
SET_A_TO_MASTER = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 7, 7: 8, 8: 26, 9: 29}
SET_A_NAMES = {0: "ebi", 1: "anago", 2: "maguro", 3: "ika", 4: "uni",
               5: "ikura", 6: "tamago", 7: "toro", 8: "tekka_maki", 9: "kappa_maki"}

# ---------------------------------------------------------------------------
# 0b. Encoding-safe file opener (handles UTF‑8 + Windows‑1252 fallback)
# ---------------------------------------------------------------------------
def smart_open(path, mode="r"):
    try:
        return open(path, mode, encoding="utf-8")
    except UnicodeDecodeError:
        return open(path, mode, encoding="cp932")


# ---------------------------------------------------------------------------
# 1.  sushi_items.csv  (100 items × attributes)
# ---------------------------------------------------------------------------
STYLE_MAP = {0: "maki", 1: "other"}
MAJOR_MAP = {0: "seafood", 1: "other"}
MINOR_MAP = {
    0:  "aomono",
    1:  "akami",
    2:  "shiromi",
    3:  "tare",
    4:  "clam_shell",
    5:  "squid_octopus",
    6:  "shrimp_crab",
    7:  "roe",
    8:  "other_seafood",
    9:  "egg",
    10: "meat_other",
    11: "vegetables",
}

def build_items_csv():
    raw_path = RAW_DIR / "sushi3.idata"
    out_path = DATA_DIR / "sushi_items.csv"

    with smart_open(raw_path) as f_in, open(out_path, "w", newline="") as f_out:
        w = csv.writer(f_out)
        w.writerow([
            "item_id",
            "name",
            "style",
            "style_label",
            "major_group",
            "major_group_label",
            "minor_group",
            "minor_group_label",
            "oiliness",
            "freq_eat",
            "freq_eat_label",
            "price_norm",
            "freq_sold",
        ])
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 9:
                continue
            item_id = int(parts[0])
            name = parts[1]
            style = int(parts[2])
            major = int(parts[3])
            minor = int(parts[4])
            # Raw scale is INVERTED: range [0-4], 0 = most heavy/oily
            # (README-en.txt, sushi3.idata feature 6). Recode so that
            # higher = more oily, which is what downstream models assume.
            oiliness = 4.0 - float(parts[5])
            freq_eat = float(parts[6])
            price_norm = float(parts[7])
            freq_sold = float(parts[8])

            freq_eat_label = "high" if freq_eat >= 2.0 else "low"

            w.writerow([
                item_id, name,
                style, STYLE_MAP.get(style, str(style)),
                major, MAJOR_MAP.get(major, str(major)),
                minor, MINOR_MAP.get(minor, str(minor)),
                round(oiliness, 4),
                round(freq_eat, 4),
                freq_eat_label,
                round(price_norm, 4),
                round(freq_sold, 4),
            ])
    return _count_rows(out_path)


# ---------------------------------------------------------------------------
# 1b. Helper: load items as dict  {item_id: {attr:val, ...}}
# ---------------------------------------------------------------------------
def load_items():
    items = {}
    path = DATA_DIR / "sushi_items.csv"
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items[int(row["item_id"])] = row
    return items


# ---------------------------------------------------------------------------
# 2.  sushi_users.csv  (5,000 users × demographics)
# ---------------------------------------------------------------------------
REGION_MAP = {
    0:  "Hokkaido",
    1:  "Tohoku",
    2:  "Hokuriku",
    3:  "Kanto_Shizuoka",
    4:  "Nagano_Yamanashi",
    5:  "Chukyo",
    6:  "Kinki",
    7:  "Chugoku",
    8:  "Shikoku",
    9:  "Kyushu",
    10: "Okinawa",
    11: "Foreign",
}
EASTWEST_MAP = {0: "Eastern_Japan", 1: "Western_Japan"}
AGE_MAP = {0: "15-19", 1: "20-29", 2: "30-39", 3: "40-49", 4: "50-59", 5: "60+"}
GENDER_MAP = {0: "male", 1: "female"}

def build_users_csv():
    raw_path = RAW_DIR / "sushi3.udata"
    out_path = DATA_DIR / "sushi_users.csv"

    with smart_open(raw_path) as f_in, open(out_path, "w", newline="") as f_out:
        w = csv.writer(f_out)
        w.writerow([
            "user_id",
            "gender",
            "gender_label",
            "age_group",
            "age_label",
            "time_taken_sec",
            "pref_childhood",
            "region_childhood",
            "region_childhood_label",
            "eastwest_childhood",
            "eastwest_childhood_label",
            "pref_current",
            "region_current",
            "region_current_label",
            "eastwest_current",
            "eastwest_current_label",
            "moved",
        ])
        for idx, line in enumerate(f_in):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 11:
                continue

            user_id = int(parts[0])
            gender = int(parts[1])
            age = int(parts[2])
            time_taken = int(parts[3])
            pref_c = int(parts[4])
            region_c = int(parts[5])
            eastwest_c = int(parts[6])
            pref_u = int(parts[7])
            region_u = int(parts[8])
            eastwest_u = int(parts[9])
            moved = int(parts[10])

            w.writerow([
                idx + 1,  # sequential user_id 1-based
                gender, GENDER_MAP.get(gender, str(gender)),
                age, AGE_MAP.get(age, str(age)),
                time_taken,
                pref_c,
                region_c, REGION_MAP.get(region_c, str(region_c)),
                eastwest_c, EASTWEST_MAP.get(eastwest_c, str(eastwest_c)),
                pref_u,
                region_u, REGION_MAP.get(region_u, str(region_u)),
                eastwest_u, EASTWEST_MAP.get(eastwest_u, str(eastwest_u)),
                moved,
            ])
    return _count_rows(out_path)


def load_users():
    users = {}
    path = DATA_DIR / "sushi_users.csv"
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users[int(row["user_id"])] = row
    return users


# ---------------------------------------------------------------------------
# 3.  Parse an .order file → list of lists of item IDs (rank 1 = list[0])
# ---------------------------------------------------------------------------
def parse_order_file(filepath):
    rankings = []
    with smart_open(filepath) as f:
        header = f.readline()  # skip header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            n_items = int(parts[1])
            item_ids = [int(x) for x in parts[2:2 + n_items]]
            rankings.append(item_ids)
    return rankings


# ---------------------------------------------------------------------------
# 4.  sushi3a_choice_long.csv — Set A, 10 alternativas, ranking completo
# ---------------------------------------------------------------------------
def build_setA_choice_long():
    order_path = RAW_DIR / "sushi3a.5000.10.order"
    out_path = DATA_DIR / "sushi3a_choice_long.csv"
    items = load_items()
    users = load_users()

    rankings = parse_order_file(order_path)

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "choice_id",
            "user_id",
            "alt_id",
            "item_id",
            "item_name",
            "chosen",
            "rank",
            "style",
            "style_label",
            "major_group",
            "major_group_label",
            "minor_group",
            "minor_group_label",
            "oiliness",
            "price_norm",
            "freq_sold",
            "gender",
            "gender_label",
            "age_group",
            "age_label",
            "childhood_region",
            "childhood_region_label",
            "current_region",
            "current_region_label",
            "eastwest_childhood",
            "eastwest_childhood_label",
            "eastwest_current",
            "eastwest_current_label",
            "moved",
            "time_taken_sec",
        ])

        for user_idx, ranking in enumerate(rankings):
            user_id = user_idx + 1
            user = users.get(user_id, {})

            for rank_pos, set_a_id in enumerate(ranking):
                # The .order file carries Set A IDs; translate to master IDs
                # before looking up attributes (see SET_A_TO_MASTER above).
                master_id = SET_A_TO_MASTER[set_a_id]
                item = items.get(master_id, {})
                assert item.get("name", "") == SET_A_NAMES[set_a_id], (
                    f"Set A mapping broken: alt {set_a_id} → master {master_id} "
                    f"is '{item.get('name')}', expected '{SET_A_NAMES[set_a_id]}'"
                )
                chosen = 1 if rank_pos == 0 else 0

                w.writerow([
                    user_id,
                    user_id,
                    set_a_id,
                    master_id,
                    item.get("name", ""),
                    chosen,
                    rank_pos + 1,
                    item.get("style", ""),
                    item.get("style_label", ""),
                    item.get("major_group", ""),
                    item.get("major_group_label", ""),
                    item.get("minor_group", ""),
                    item.get("minor_group_label", ""),
                    item.get("oiliness", ""),
                    item.get("price_norm", ""),
                    item.get("freq_sold", ""),
                    user.get("gender", ""),
                    user.get("gender_label", ""),
                    user.get("age_group", ""),
                    user.get("age_label", ""),
                    user.get("region_childhood", ""),
                    user.get("region_childhood_label", ""),
                    user.get("region_current", ""),
                    user.get("region_current_label", ""),
                    user.get("eastwest_childhood", ""),
                    user.get("eastwest_childhood_label", ""),
                    user.get("eastwest_current", ""),
                    user.get("eastwest_current_label", ""),
                    user.get("moved", ""),
                    user.get("time_taken_sec", ""),
                ])
    return _count_rows(out_path)


# ---------------------------------------------------------------------------
# 5.  sushi3b_consideration_long.csv — Set B, consideration set real
#     (los 10 ítems que cada usuario realmente rankeó)
# ---------------------------------------------------------------------------
def build_setB_consideration_long():
    order_path = RAW_DIR / "sushi3b.5000.10.order"
    out_path = DATA_DIR / "sushi3b_consideration_long.csv"
    items = load_items()
    users = load_users()

    rankings = parse_order_file(order_path)

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        header = [
            "choice_id",
            "user_id",
            "item_id",
            "item_name",
            "chosen",
            "rank",
            "style",
            "style_label",
            "major_group",
            "major_group_label",
            "minor_group",
            "minor_group_label",
            "oiliness",
            "price_norm",
            "freq_sold",
            "gender",
            "gender_label",
            "age_group",
            "age_label",
            "childhood_region",
            "childhood_region_label",
            "current_region",
            "current_region_label",
            "eastwest_childhood",
            "eastwest_childhood_label",
            "eastwest_current",
            "eastwest_current_label",
            "moved",
            "time_taken_sec",
            "choice_set_type",
        ]
        w.writerow(header)

        for user_idx, ranking in enumerate(rankings):
            user_id = user_idx + 1
            user = users.get(user_id, {})

            for rank_pos, item_id in enumerate(ranking):
                item = items.get(item_id, {})
                chosen = 1 if rank_pos == 0 else 0

                w.writerow([
                    user_id,
                    user_id,
                    item_id,
                    item.get("name", ""),
                    chosen,
                    rank_pos + 1,
                    item.get("style", ""),
                    item.get("style_label", ""),
                    item.get("major_group", ""),
                    item.get("major_group_label", ""),
                    item.get("minor_group", ""),
                    item.get("minor_group_label", ""),
                    item.get("oiliness", ""),
                    item.get("price_norm", ""),
                    item.get("freq_sold", ""),
                    user.get("gender", ""),
                    user.get("gender_label", ""),
                    user.get("age_group", ""),
                    user.get("age_label", ""),
                    user.get("region_childhood", ""),
                    user.get("region_childhood_label", ""),
                    user.get("region_current", ""),
                    user.get("region_current_label", ""),
                    user.get("eastwest_childhood", ""),
                    user.get("eastwest_childhood_label", ""),
                    user.get("eastwest_current", ""),
                    user.get("eastwest_current_label", ""),
                    user.get("moved", ""),
                    user.get("time_taken_sec", ""),
                    "consideration_set",
                ])
    return _count_rows(out_path)


# ---------------------------------------------------------------------------
# 6.  sushi3b_choice_long.csv — Set B, sampled choice set (McFadden 1978)
#     chosen = rank #1  +  9 random non‑ranked alternatives sampled uniformly
# ---------------------------------------------------------------------------
def build_setB_choice_long():
    order_path = RAW_DIR / "sushi3b.5000.10.order"
    out_path = DATA_DIR / "sushi3b_choice_long.csv"
    items = load_items()
    users = load_users()
    all_item_ids = sorted(items.keys())  # 0..99

    rankings = parse_order_file(order_path)

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "choice_id",
            "user_id",
            "item_id",
            "item_name",
            "chosen",
            "rank",
            "style",
            "style_label",
            "major_group",
            "major_group_label",
            "minor_group",
            "minor_group_label",
            "oiliness",
            "price_norm",
            "freq_sold",
            "gender",
            "gender_label",
            "age_group",
            "age_label",
            "childhood_region",
            "childhood_region_label",
            "current_region",
            "current_region_label",
            "eastwest_childhood",
            "eastwest_childhood_label",
            "eastwest_current",
            "eastwest_current_label",
            "moved",
            "time_taken_sec",
            "choice_set_type",
        ])

        for user_idx, ranking in enumerate(rankings):
            user_id = user_idx + 1
            user = users.get(user_id, {})

            chosen_item = ranking[0]
            ranked_set = set(ranking)

            unranked = [i for i in all_item_ids if i not in ranked_set]
            sampled = random.sample(unranked, min(N_ALTERNATIVES_SAMPLE, len(unranked)))

            # Build rows: chosen + sampled non‑chosen
            rows_for_user = []

            for alt_idx, item_id in enumerate([chosen_item] + sampled):
                item = items.get(item_id, {})
                chosen = 1 if alt_idx == 0 else 0
                rows_for_user.append([
                    user_id,
                    user_id,
                    item_id,
                    item.get("name", ""),
                    chosen,
                    1 if chosen else "",
                    item.get("style", ""),
                    item.get("style_label", ""),
                    item.get("major_group", ""),
                    item.get("major_group_label", ""),
                    item.get("minor_group", ""),
                    item.get("minor_group_label", ""),
                    item.get("oiliness", ""),
                    item.get("price_norm", ""),
                    item.get("freq_sold", ""),
                    user.get("gender", ""),
                    user.get("gender_label", ""),
                    user.get("age_group", ""),
                    user.get("age_label", ""),
                    user.get("region_childhood", ""),
                    user.get("region_childhood_label", ""),
                    user.get("region_current", ""),
                    user.get("region_current_label", ""),
                    user.get("eastwest_childhood", ""),
                    user.get("eastwest_childhood_label", ""),
                    user.get("eastwest_current", ""),
                    user.get("eastwest_current_label", ""),
                    user.get("moved", ""),
                    user.get("time_taken_sec", ""),
                    "sampled",
                ])

            # Shuffle so the chosen item is not always the first row
            random.shuffle(rows_for_user)
            for row in rows_for_user:
                w.writerow(row)

    return _count_rows(out_path)


# ---------------------------------------------------------------------------
# 7.  sushi3b_score_long.csv — Score matrix in long format
# ---------------------------------------------------------------------------
def build_score_long():
    raw_path = RAW_DIR / "sushi3b.5000.10.score"
    out_path = DATA_DIR / "sushi3b_score_long.csv"
    items = load_items()

    all_rows = []
    with smart_open(raw_path) as f_in:
        for user_idx, line in enumerate(f_in):
            line = line.strip()
            if not line:
                continue
            scores_list = [int(v) for v in line.split()]
            if len(scores_list) >= 100:
                user_id = user_idx + 1
                for col, score_val in enumerate(scores_list[:100]):
                    item = items.get(col, {})
                    scored = 1 if score_val >= 0 else 0
                    score_out = score_val if score_val >= 0 else ""
                    all_rows.append([
                        user_id,
                        col,
                        item.get("name", ""),
                        score_out,
                        scored,
                    ])

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["user_id", "item_id", "item_name", "score", "scored"])
        for row in all_rows:
            w.writerow(row)

    return len(all_rows)


# ---------------------------------------------------------------------------
# 8.  data_dictionary.txt  — Full documentation
# ---------------------------------------------------------------------------
def write_data_dictionary(n_sushi3a, n_sushi3b_sampled, n_sushi3b_cons, n_score):
    dd_path = DATA_DIR / "data_dictionary.txt"
    with open(dd_path, "w", encoding="utf-8") as f:
        f.write("""================================================================================
DATA DICTIONARY — Sushi Preference Dataset (Kamishima, 2003)
================================================================================

ORIGIN
------
Dataset  : SUSHI Preference Data Sets
Author   : Toshihiro Kamishima (National Institute of Advanced Industrial
           Science and Technology, Japan)
Paper    : Kamishima, T. (2003). "Nantonac Collaborative Filtering:
           Recommendation Based on Order Responses." KDD2003, pp. 583-588.
Source   : https://www.kamishima.net/sushi/
License  : Research use only. Redistribution requires author permission.

DATA TYPE
---------
Revealed preference (stated preference through questionnaire survey).
5,000 real Japanese consumers ranked sushi types by preference (ranking method)
and scored them on a 5-point scale (scoring method). The items are real sushi
types with real market attributes (price, oiliness, style, etc.).

================================================================================
FILE LIST
================================================================================

Generated files in data/:

  1. sushi_items.csv           — 100 sushi items with attributes
  2. sushi_users.csv           — 5,000 users with demographics
  3. sushi3a_choice_long.csv   — DISCRETE CHOICE: Set A (10 alt, full ranking)
  4. sushi3b_choice_long.csv   — DISCRETE CHOICE: Set B (100 alt, sampled)
  5. sushi3b_consideration_long.csv — DISCRETE CHOICE: Set B, real consideration set
  6. sushi3b_score_long.csv    — Score matrix in long format (optional)

Raw files in data/sushi_raw/:

  sushi3.idata               — 100 items × 9 attributes
  sushi3.udata               — 5,000 users × 11 demographics
  sushi3a.5000.10.order      — 5,000 × 10 item rankings (Set A, 10 items)
  sushi3b.5000.10.order      — 5,000 × 10 item rankings (Set B, 100 items)
  sushi3b.5000.10.score      — 5,000 × 100 score matrix
  README-en.txt              — Original documentation (English)

================================================================================
1. sushi_items.csv  (100 rows)
================================================================================

Column                Type      Description
--------------------- --------- -------------------------------------------------
item_id               int       Item ID (0-99), matching row in sushi3.idata
name                  str       Name in Japanese romanized alphabet
style                 int       0 = maki (roll), 1 = other (nigiri, etc.)
style_label           str       "maki" or "other"
major_group           int       0 = seafood, 1 = other (egg, meat, vegetables)
major_group_label     str       "seafood" or "other"
minor_group           int       0-11 (see MINOR GROUP LEGEND below)
minor_group_label     str       Label for minor group
oiliness              float     Taste oiliness, higher = MORE oily. RECODED as
                                (4 - raw): the raw sushi3.idata scale is inverted
                                (0 = most heavy/oily, per README-en.txt).
                                Recoded range ≈ [0.27, 3.45]; e.g. toro 3.45,
                                kappa_maki 0.27.
freq_eat              float     How frequently eaten [1.0, 2.3], higher = more
freq_eat_label        str       "high" if freq_eat >= 2.0 else "low"
price_norm            float     Normalized market price [1.00, 4.49]
freq_sold             float     Frequency sold in shops [0.20, 0.92]

MINOR GROUP LEGEND
  0  = aomono (blue-skinned fish: saba, aji, iwashi, sanma)
  1  = akami (red meat fish: maguro, toro, katsuo)
  2  = shiromi (white-meat fish: tai, hirame, suzuki)
  3  = tare (baste-style: anago, unagi)
  4  = clam_shell (hotategai, akagai, awabi, hamaguri)
  5  = squid_octopus (ika, tako, geso)
  6  = shrimp_crab (ebi, amaebi, kani, botanebi, tarabagani)
  7  = roe (ikura, kazunoko, tobiko, mentaiko, tarako)
  8  = other_seafood (uni, kanimiso, ankimo)
  9  = egg (tamago)
  10 = meat_other (gyusashi, basashi, kujira, kamo, sasami)
  11 = vegetables (kappa_maki, nattou_maki, takuwan_maki, inari, ume_shiso_maki)

================================================================================
2. sushi_users.csv  (5,000 rows)
================================================================================

Column                    Type    Description
------------------------- ------- -----------------------------------------------
user_id                   int     Sequential user ID (1-5000)
gender                    int     0 = male, 1 = female
gender_label              str     "male" or "female"
age_group                 int     0-5
age_label                 str     Age bracket: 15-19, 20-29, 30-39, 40-49, 50-59, 60+
time_taken_sec            int     Total seconds to fill questionnaire
pref_childhood            int     Prefecture ID where lived longest before age 15
region_childhood          int     Region ID where lived longest before age 15 (0-11)
region_childhood_label    str     Region name (Hokkaido, Tohoku, Kanto, Kinki, etc.)
eastwest_childhood        int     0 = Eastern Japan, 1 = Western Japan
eastwest_childhood_label  str     "Eastern_Japan" or "Western_Japan"
pref_current              int     Prefecture ID of current residence
region_current            int     Region ID of current residence (0-11)
region_current_label      str     Region name
eastwest_current          int     0 = Eastern, 1 = Western (based on current residence)
eastwest_current_label    str     "Eastern_Japan" or "Western_Japan"
moved                     int     0 = childhood pref == current pref, 1 = different

REGION LEGEND
  0  = Hokkaido
  1  = Tohoku            (Aomori, Iwate, Akita, Miyagi, Yamagata, Fukushima)
  2  = Hokuriku           (Niigata, Toyama, Ishikawa, Fukui)
  3  = Kanto_Shizuoka     (Ibaraki, Tochigi, Gunma, Saitama, Chiba, Tokyo, Kanagawa, Shizuoka)
  4  = Nagano_Yamanashi   (Yamanashi, Nagano)
  5  = Chukyo             (Aichi, Gifu, Mie)
  6  = Kinki              (Shiga, Kyoto, Osaka, Nara, Wakayama, Hyogo)
  7  = Chugoku            (Okayama, Hiroshima, Tottori, Shimane, Yamaguchi)
  8  = Shikoku            (Ehime, Kagawa, Tokushima, Kochi)
  9  = Kyushu             (Fukuoka, Nagasaki, Saga, Kumamoto, Kagoshima, Miyazaki, Oita)
  10 = Okinawa
  11 = Foreign

NOTE: Rows 323, 617, 1431, 4667 correspond to the authors (Kamishima, Akaho,
Kazawa, Fujiki respectively).

================================================================================
3. sushi3a_choice_long.csv — Discrete Choice: Set A
================================================================================

SET A ITEMS (10 alternatives, full ranking by all 5,000 users):

  alt_id  name        (English)        master item_id in sushi_items.csv
  ------  ----------  ---------------  ---------------------------------
  0       ebi         shrimp           0
  1       anago       sea eel          1
  2       maguro      tuna             2
  3       ika         squid            3
  4       uni         sea urchin       4
  5       ikura       salmon roe       6
  6       tamago      egg              7
  7       toro        fatty tuna       8
  8       tekka_maki  tuna roll        26
  9       kappa_maki  cucumber roll    29

IMPORTANT — ID MAPPING: sushi3a.5000.10.order uses Set A's own numbering
(alt_id, 0-9), which differs from the master 100-item numbering for IDs 5-9
(master 5 = tako and master 9 = amaebi are NOT part of Set A). Attributes are
joined via the mapping above. Use item_id to join against sushi_items.csv;
use alt_id as the alternative index in choice models.

FORMAT: Long format, one row per user-alternative pair
  Total rows: """ + str(n_sushi3a) + """
  Rows per user: 10 (all alternatives in Set A)
  Choice sets: 5,000

Column                Description
--------------------- ----------------------------------------------------------
choice_id             Choice occasion ID (= user_id in this case)
user_id               User identifier (1-5000)
alt_id                Set A alternative index (0-9, see mapping table above)
item_id               Master item identifier (joins with sushi_items.csv)
item_name             Sushi name
chosen                1 if item was ranked #1 (most preferred), 0 otherwise
rank                  Preference rank (1 = most preferred, ..., 10 = least)
Item attributes:
  style, style_label, major_group, major_group_label,
  minor_group, minor_group_label, oiliness, price_norm, freq_sold
User characteristics:
  gender, gender_label, age_group, age_label,
  childhood_region, childhood_region_label,
  current_region, current_region_label,
  eastwest_childhood, eastwest_childhood_label,
  eastwest_current, eastwest_current_label,
  moved, time_taken_sec

CHOICE FREQUENCIES (Set A — most preferred item):
  Users choose exactly 1 item. Since each user gives a full ranking of all 10
  items, the chosen item is always the #1 in their personal ranking.

================================================================================
4. sushi3b_choice_long.csv — Discrete Choice: Set B (sampled)
================================================================================

SET B ITEMS (100 alternatives, each user ranked only 10 of them):
  All 100 sushi types listed in sushi_items.csv.

METHODOLOGY:
  For each user, the #1 ranked item = chosen (chosen=1).
  From the remaining 99 items (those the user did NOT rank), 9 are sampled
  uniformly at random and included as non-chosen alternatives (chosen=0).
  This follows McFadden's (1978) sampling-of-alternatives method: under the
  Uniform Conditioning Property, MLE with sampled choice sets yields consistent
  parameter estimates.

  SEED = 42 for reproducibility.

FORMAT: Identical columns to sushi3a_choice_long.csv, plus:
  choice_set_type = "sampled"

  Total rows: """ + str(n_sushi3b_sampled) + """
  Rows per user: 10 (1 chosen + 9 sampled non-chosen)
  Choice sets: 5,000

================================================================================
5. sushi3b_consideration_long.csv — Discrete Choice: Set B (consideration set)
================================================================================

METHODOLOGY:
  For each user, all 10 items they actually ranked are included.
  The #1 ranked = chosen (chosen=1), ranks 2-10 = not chosen (chosen=0).
  This represents the user's REAL consideration set — the items they were
  willing and able to evaluate.

  Total rows: """ + str(n_sushi3b_cons) + """
  Rows per user: 10
  Choice sets: 5,000

FORMAT: Identical columns to sushi3a_choice_long.csv, plus:
  choice_set_type = "consideration_set"

================================================================================
6. sushi3b_score_long.csv — Score matrix
================================================================================

Score data from the scoring method (Step 2 of the survey).
Each user rated items on a 5-point scale:
  0 = most disliked, 4 = most preferred, -1/blank = not rated.

  Total rows: """ + str(n_score) + """
  Columns: user_id, item_id, item_name, score, scored (1 if rated, 0 if not)

================================================================================
SUGGESTED NESTING STRUCTURES FOR NESTED LOGIT
================================================================================

The item attributes offer several natural nesting possibilities:

1. Ingredient-based (minor_group): 12 nests
   - High within-nest correlation expected (consumer substitutes within
     the same protein type: tuna for tuna, white fish for white fish)

2. Style-based (style): 2 nests — maki vs. other
   - Roll vs. nigiri/gunkan consumers

3. Price-based (price_norm tertiles):
   - Economy, mid-range, premium

4. Oiliness-based (oiliness tertiles):
   - Lean, medium, fatty — health-conscious vs. taste-preferring consumers

================================================================================
MODELS THAT CAN BE ESTIMATED
================================================================================

| Model              | Packages    | Notes                                   |
|--------------------|-------------|-----------------------------------------|
| MNL (base)         | mlogit/Apollo | ASCs + taste parameters                |
| MNL + interactions | mlogit/Apollo | price×age, oiliness×eastwest, etc.     |
| Nested Logit       | mlogit/Apollo | Nests by ingredient, style, or price    |
| Mixed Logit        | mlogit/Apollo | Heterogeneity in price sensitivity      |
| Latent Class       | gmnl/Apollo   | Segments: traditionalist, adventurer, etc. |
| Hybrid Choice      | Apollo        | Latent variable "culinary sophistication" |

================================================================================
REPRODUCIBILITY
================================================================================

  python scripts/process_sushi_dataset.py

Processes raw files in data/sushi_raw/ → generates all CSVs in data/
SEED = 42 for sampling. All outputs are deterministic.

================================================================================
KNOWN LIMITATIONS
================================================================================

1. The data comes from a questionnaire survey, not from actual purchase
   transactions. This is "stated" rather than "revealed" preference.
   However, respondents are real consumers evaluating real products with
   real market attributes.

2. Set A has only 10 alternatives. Useful for clean baseline models but
   limits nesting depth.

3. Set B sampling introduces a trade-off: fewer alternatives per choice set
   (10 out of 100) reduces efficiency but is computationally lighter.

4. Users 323, 617, 1431, 4667 are the paper authors. Their responses may
   differ systematically from the general population.

================================================================================
""")
    return dd_path


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _count_rows(path):
    with open(path) as f:
        return sum(1 for _ in f) - 1  # exclude header


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("SUSHI Preference Dataset — Discrete Choice Pipeline")
    print("=" * 60)

    # 1. Items
    n = build_items_csv()
    print(f"  [1/6] sushi_items.csv          → {n:>6,} rows (100 items)")

    # 2. Users
    n = build_users_csv()
    print(f"  [2/6] sushi_users.csv          → {n:>6,} rows (5,000 users)")

    # 3. Set A choice long
    n = build_setA_choice_long()
    print(f"  [3/6] sushi3a_choice_long.csv  → {n:>6,} rows (5,000 × 10)")

    # 4. Set B consideration long
    n = build_setB_consideration_long()
    print(f"  [4/6] sushi3b_consideration..  → {n:>6,} rows (5,000 × 10)")

    # 5. Set B sampled choice long
    n = build_setB_choice_long()
    print(f"  [5/6] sushi3b_choice_long.csv  → {n:>6,} rows (5,000 × 10)")

    # 6. Score long
    n = build_score_long()
    print(f"  [6/6] sushi3b_score_long.csv   → {n:>6,} rows (5,000 × 100)")

    # 7. Data dictionary
    n_sushi3a = _count_rows(DATA_DIR / "sushi3a_choice_long.csv")
    n_sushi3b_sampled = _count_rows(DATA_DIR / "sushi3b_choice_long.csv")
    n_sushi3b_cons = _count_rows(DATA_DIR / "sushi3b_consideration_long.csv")
    n_score = _count_rows(DATA_DIR / "sushi3b_score_long.csv")
    dd = write_data_dictionary(n_sushi3a, n_sushi3b_sampled, n_sushi3b_cons, n_score)
    print(f"  [DOC] data_dictionary.txt       → written")

    # Summary
    print("\n" + "=" * 60)
    print("OUTPUT SUMMARY")
    print("=" * 60)
    print(f"  sushi_items.csv                  : {_count_rows(DATA_DIR / 'sushi_items.csv'):>6,} rows")
    print(f"  sushi_users.csv                  : {_count_rows(DATA_DIR / 'sushi_users.csv'):>6,} rows")
    print(f"  sushi3a_choice_long.csv          : {_count_rows(DATA_DIR / 'sushi3a_choice_long.csv'):>6,} rows")
    print(f"  sushi3b_consideration_long.csv   : {_count_rows(DATA_DIR / 'sushi3b_consideration_long.csv'):>6,} rows")
    print(f"  sushi3b_choice_long.csv          : {_count_rows(DATA_DIR / 'sushi3b_choice_long.csv'):>6,} rows")
    print(f"  sushi3b_score_long.csv           : {_count_rows(DATA_DIR / 'sushi3b_score_long.csv'):>6,} rows")
    print(f"  data_dictionary.txt              : documentation")

    print(f"\n  Total rows across all CSVs       : {_count_rows(DATA_DIR / 'sushi_items.csv') + _count_rows(DATA_DIR / 'sushi_users.csv') + _count_rows(DATA_DIR / 'sushi3a_choice_long.csv') + _count_rows(DATA_DIR / 'sushi3b_consideration_long.csv') + _count_rows(DATA_DIR / 'sushi3b_choice_long.csv') + _count_rows(DATA_DIR / 'sushi3b_score_long.csv'):>6,}")

    print("\n  Pipeline complete. All files in data/")
    print("  Next: verify with scripts/verify_sushi_dataset.py")


if __name__ == "__main__":
    main()
