"""
verify_sushi_dataset.py
=======================
Integrity checks for the processed SUSHI discrete-choice dataset.

Run after: python scripts/process_sushi_dataset.py
"""

import csv
import sys
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

SEPARATOR = "=" * 65


def load_csv(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def verify(fname, checks):
    """Run a named list of checks, returning (passed, failed)."""
    print(f"\n  File: {fname}")
    passed = 0
    failed = 0
    for desc, result in checks:
        if result:
            print(f"    [PASS] {desc}")
            passed += 1
        else:
            print(f"    [FAIL] {desc}")
            failed += 1
    return passed, failed


def main():
    print(SEPARATOR)
    print("VERIFICATION — Sushi Preference Discrete Choice Dataset")
    print(SEPARATOR)

    total_pass = 0
    total_fail = 0

    # -------------------------------------------------------------------
    # sushi_items.csv
    # -------------------------------------------------------------------
    rows = load_csv(DATA_DIR / "sushi_items.csv")
    item_ids = {int(r["item_id"]) for r in rows}

    checks = [
        ("100 rows", len(rows) == 100),
        ("All item_ids 0-99 present", item_ids == set(range(100))),
        ("style in {0,1}", all(int(r["style"]) in (0, 1) for r in rows)),
        ("major_group in {0,1}", all(int(r["major_group"]) in (0, 1) for r in rows)),
        ("minor_group in 0-11", all(0 <= int(r["minor_group"]) <= 11 for r in rows)),
        ("oiliness in [0.5, 4.0]", all(0.0 < float(r["oiliness"]) < 5.0 for r in rows)),
        ("price_norm in [1.0, 5.0]", all(1.0 <= float(r["price_norm"]) <= 5.0 for r in rows)),
        ("freq_sold in [0.0, 1.0]", all(0.0 <= float(r["freq_sold"]) <= 1.0 for r in rows)),
    ]
    p, f = verify("sushi_items.csv", checks)
    total_pass += p
    total_fail += f

    # -------------------------------------------------------------------
    # sushi_users.csv
    # -------------------------------------------------------------------
    rows = load_csv(DATA_DIR / "sushi_users.csv")
    user_ids = {int(r["user_id"]) for r in rows}

    checks = [
        ("5,000 rows", len(rows) == 5000),
        ("User IDs 1-5000", user_ids == set(range(1, 5001))),
        ("gender in {0,1}", all(int(r["gender"]) in (0, 1) for r in rows)),
        ("age_group in 0-5", all(0 <= int(r["age_group"]) <= 5 for r in rows)),
        ("eastwest in {0,1}", all(int(r["eastwest_childhood"]) in (0, 1) for r in rows)),
        ("eastwest_current in {0,1}", all(int(r["eastwest_current"]) in (0, 1) for r in rows)),
        ("moved in {0,1}", all(int(r["moved"]) in (0, 1) for r in rows)),
        ("No empty demographics", all(r["gender_label"] != "" for r in rows)),
    ]
    p, f = verify("sushi_users.csv", checks)
    total_pass += p
    total_fail += f

    # -------------------------------------------------------------------
    # sushi3a_choice_long.csv
    # -------------------------------------------------------------------
    rows = load_csv(DATA_DIR / "sushi3a_choice_long.csv")

    by_cid = {}
    for r in rows:
        cid = int(r["choice_id"])
        by_cid.setdefault(cid, []).append(r)

    n_chosen_per_cid = Counter()
    n_alts_per_cid = Counter()
    for cid, rs in by_cid.items():
        n_chosen_per_cid[sum(1 for r in rs if r["chosen"] == "1")] += 1
        n_alts_per_cid[len(rs)] += 1

    # Official Set A legend (README-en.txt): alt_id → (name, master item_id).
    # Master IDs 5-9 are tako..amaebi, which are NOT in Set A — a join done
    # with the wrong numbering mislabels half the choice set, so this mapping
    # is verified explicitly.
    SET_A_LEGEND = {
        0: ("ebi", 0), 1: ("anago", 1), 2: ("maguro", 2), 3: ("ika", 3),
        4: ("uni", 4), 5: ("ikura", 6), 6: ("tamago", 7), 7: ("toro", 8),
        8: ("tekka_maki", 26), 9: ("kappa_maki", 29),
    }
    observed_map = {int(r["alt_id"]): (r["item_name"], int(r["item_id"]))
                    for r in rows}
    oil_by_name = {r["item_name"]: float(r["oiliness"]) for r in rows}

    checks_setA = [
        ("50,000 rows", len(rows) == 50000),
        ("5,000 choice_ids", len(by_cid) == 5000),
        ("Exactly 1 chosen per choice_id",
         n_chosen_per_cid.get(1, 0) == 5000),
        ("Exactly 10 alternatives per choice_id",
         n_alts_per_cid.get(10, 0) == 5000),
        ("All alt_ids 0-9", all(int(r["alt_id"]) in range(10) for r in rows)),
        ("Set A item mapping matches README legend (names + master IDs)",
         observed_map == SET_A_LEGEND),
        ("tako/amaebi NOT present (would indicate broken Set A join)",
         not any(r["item_name"] in ("tako", "amaebi") for r in rows)),
        ("oiliness direction: toro (fatty tuna) > kappa_maki (cucumber roll)",
         oil_by_name.get("toro", 0) > oil_by_name.get("kappa_maki", 99)),
        ("maki rolls flagged as style=maki",
         all(r["style_label"] == "maki"
             for r in rows if r["item_name"] in ("tekka_maki", "kappa_maki"))),
        ("No missing price_norm", all(r["price_norm"] != "" for r in rows)),
        ("No missing oiliness", all(r["oiliness"] != "" for r in rows)),
        ("Chosen item has rank=1",
         all(r["rank"] == "1" for r in rows if r["chosen"] == "1")),
    ]
    p, f = verify("sushi3a_choice_long.csv", checks_setA)
    total_pass += p
    total_fail += f

    # Distribution of chosen items in Set A
    chosen_dist = Counter(r["item_name"] for r in rows if r["chosen"] == "1")
    print(f"\n    Chosen item distribution (Set A top 3):")
    for item, count in chosen_dist.most_common(5):
        print(f"      {item:20s}: {count:>5,} ({100 * count / 5000:.1f}%)")

    # -------------------------------------------------------------------
    # sushi3b_consideration_long.csv
    # -------------------------------------------------------------------
    rows = load_csv(DATA_DIR / "sushi3b_consideration_long.csv")

    by_cid = {}
    for r in rows:
        cid = int(r["choice_id"])
        by_cid.setdefault(cid, []).append(r)

    n_chosen = sum(1 for r in rows if r["chosen"] == "1")
    item_ids_b = {int(r["item_id"]) for r in rows}

    checks_cons = [
        ("50,000 rows", len(rows) == 50000),
        ("5,000 choice_ids", len(by_cid) == 5000),
        ("5,000 chosen=1 (exactly 1/user)", n_chosen == 5000),
        ("10 alternatives per choice_id",
         all(len(rs) == 10 for rs in by_cid.values())),
        ("All item_ids in 0-99", item_ids_b.issubset(set(range(100)))),
        ("choice_set_type = consideration_set",
         all(r["choice_set_type"] == "consideration_set" for r in rows)),
    ]
    p, f = verify("sushi3b_consideration_long.csv", checks_cons)
    total_pass += p
    total_fail += f

    # -------------------------------------------------------------------
    # sushi3b_choice_long.csv
    # -------------------------------------------------------------------
    rows = load_csv(DATA_DIR / "sushi3b_choice_long.csv")

    by_cid = {}
    for r in rows:
        cid = int(r["choice_id"])
        by_cid.setdefault(cid, []).append(r)

    n_chosen = sum(1 for r in rows if r["chosen"] == "1")
    items_per_cid = Counter(len(rs) for rs in by_cid.values())
    all_items = {int(r["item_id"]) for r in rows}

    checks_sampled = [
        ("50,000 rows", len(rows) == 50000),
        ("5,000 choice_ids", len(by_cid) == 5000),
        ("5,000 chosen=1", n_chosen == 5000),
        ("10 alternatives per choice_id",
         items_per_cid.get(10, 0) == 5000),
        ("All item_ids in 0-99", all_items.issubset(set(range(100)))),
        ("Has at least 40 unique items across all samples",
         len(all_items) >= 40),
        ("choice_set_type = sampled",
         all(r["choice_set_type"] == "sampled" for r in rows)),
    ]
    p, f = verify("sushi3b_choice_long.csv", checks_sampled)
    total_pass += p
    total_fail += f

    # -------------------------------------------------------------------
    # sushi3b_score_long.csv
    # -------------------------------------------------------------------
    rows = load_csv(DATA_DIR / "sushi3b_score_long.csv")

    by_user = {}
    for r in rows:
        uid = int(r["user_id"])
        by_user.setdefault(uid, []).append(r)

    scored = sum(1 for r in rows if r["scored"] == "1")
    not_scored = sum(1 for r in rows if r["scored"] == "0")

    checks_score = [
        ("500,000 rows", len(rows) == 500000),
        ("5,000 user_ids", len(by_user) == 5000),
        ("100 items per user", all(len(rs) == 100 for rs in by_user.values())),
        ("scored values 0-4",
         all(int(r["score"]) in (0, 1, 2, 3, 4) for r in rows if r["scored"] == "1")),
    ]
    p, f = verify("sushi3b_score_long.csv", checks_score)
    total_pass += p
    total_fail += f

    print(f"\n    Score coverage: {scored:,} rated ({100*scored/(scored+not_scored):.1f}%)"
          f" vs {not_scored:,} not rated")

    # -------------------------------------------------------------------
    # data_dictionary.txt
    # -------------------------------------------------------------------
    dd_path = DATA_DIR / "data_dictionary.txt"
    checks_dd = [
        ("data_dictionary.txt exists", dd_path.exists()),
        ("data_dictionary.txt > 5 KB", dd_path.stat().st_size > 5000),
    ]
    p, f = verify("data_dictionary.txt", checks_dd)
    total_pass += p
    total_fail += f

    # -------------------------------------------------------------------
    # Final summary
    # -------------------------------------------------------------------
    print(f"\n{SEPARATOR}")
    print(f"VERIFICATION RESULT:  {total_pass} PASSED  /  {total_fail} FAILED")
    print(SEPARATOR)
    if total_fail == 0:
        print("All checks passed. Dataset is ready for discrete choice estimation.")
    else:
        print(f"{total_fail} checks FAILED. Review the output above.")
    print(SEPARATOR)

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
