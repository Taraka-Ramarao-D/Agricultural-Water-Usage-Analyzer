"""
Agricultural Water Usage Analyzer
Case Study 16 (Batch-16) - Agriculture | A9502 Programming for Problem Solving Laboratory

Pipeline:
  1. Generate / load irrigation records (CSV file handling)
  2. Clean and validate the data
  3. Compute totals, percentages and rates
  4. Compare crops, regions and months
  5. Print recommendations and save tables + charts

Run:   python water_usage_analyzer.py
"""

import csv
import os
import random
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAW_FILE = "irrigation_records_raw.csv"
CLEAN_FILE = "irrigation_records_clean.csv"
OUT_DIR = "output"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# crop -> (typical water need in mm per irrigation, growing months, method)
CROPS = {
    "Rice":      (120, [6, 7, 8, 9, 10], "Flood"),
    "Sugarcane": (140, [1, 2, 3, 4, 5, 6, 11, 12], "Flood"),
    "Cotton":    (80, [6, 7, 8, 9, 10, 11], "Furrow"),
    "Maize":     (60, [6, 7, 8, 9, 10], "Sprinkler"),
    "Wheat":     (55, [11, 12, 1, 2, 3], "Furrow"),
    "Groundnut": (45, [6, 7, 8, 9, 10], "Sprinkler"),
    "Tomato":    (50, [10, 11, 12, 1, 2], "Drip"),
    "Chilli":    (48, [7, 8, 9, 10, 11, 12], "Drip"),
}

# region -> (water-use multiplier, area factor)
REGIONS = {
    "Nizamabad": (1.15, 1.0),
    "Warangal": (1.00, 1.0),
    "Karimnagar": (1.05, 1.0),
    "Medak":     (0.85, 1.0),
    "Mahabubnagar": (0.80, 1.0),
}

SEASON_FACTOR = {1: 0.9, 2: 1.0, 3: 1.15, 4: 1.3, 5: 1.35, 6: 0.9,
                 7: 0.6, 8: 0.6, 9: 0.7, 10: 0.8, 11: 0.85, 12: 0.9}


# ---------------------------------------------------------------- data ----
def generate_raw_data(path, n=600, seed=16):
    """Create a realistic irrigation log with deliberate data-quality issues."""
    random.seed(seed)
    rows = []
    for rid in range(1, n + 1):

        crop = random.choice(list(CROPS))
        need, months, method = CROPS[crop]
        region = random.choice(list(REGIONS))
        mult = REGIONS[region][0]
        month = random.choice(months)
        area = round(random.uniform(0.5, 6.0), 2)            # hectares
        # 1 mm over 1 ha = 10 m3 (10,000 litres)
        mm = need * mult * SEASON_FACTOR[month] * random.uniform(0.85, 1.15)
        events = random.randint(2, 6)
        water_m3 = round(mm * 10 * area * events / 3, 1)
        rows.append([rid, f"F{random.randint(100, 999)}", region, crop,
                     month, area, method, water_m3])

    # inject faults so the cleaning step has real work to do
    for _ in range(18):                                        # missing values
        r = random.choice(rows)
        r[random.choice([5, 7])] = ""
    for _ in range(10):                                        # negatives
        random.choice(rows)[7] = -abs(random.randint(50, 500))
    for _ in range(8):                                         # absurd outliers
        random.choice(rows)[7] = random.randint(90000, 250000)
    for _ in range(14):                                        # text inconsistency
        r = random.choice(rows)
        r[3] = random.choice([r[3].upper(), r[3].lower(), " " + r[3] + " "])
    for _ in range(6):                                         # invalid month
        random.choice(rows)[4] = random.choice([0, 13, 15])
    rows += [list(random.choice(rows)) for _ in range(12)]     # duplicates

    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["record_id", "farm_id", "region", "crop", "month",
                     "area_ha", "irrigation_method", "water_used_m3"])
        w.writerows(rows)
    return len(rows)


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------ cleaning ----
def clean_data(records):
    """Return (clean_records, report_dict)."""
    report = defaultdict(int)
    report["raw_rows"] = len(records)
    seen = set()
    clean = []
    for r in records:
        key = tuple(r.values())
        if key in seen:
            report["duplicates_removed"] += 1
            continue
        seen.add(key)

        r["crop"] = r["crop"].strip().title()
        r["region"] = r["region"].strip().title()
        r["irrigation_method"] = r["irrigation_method"].strip().title()

        if r["area_ha"] == "" or r["water_used_m3"] == "":
             report["missing_values_removed"] += 1
             continue
        try:
             r["area_ha"] = float(r["area_ha"])
             r["water_used_m3"] = float(r["water_used_m3"])
             r["month"] = int(r["month"])
        except ValueError:
             report["non_numeric_removed"] += 1
             continue
        if r["water_used_m3"] <= 0 or r["area_ha"] <= 0:
             report["negative_or_zero_removed"] += 1
             continue
        if not 1 <= r["month"] <= 12:
             report["invalid_month_removed"] += 1
             continue
        if r["crop"] not in CROPS or r["region"] not in REGIONS:
             report["unknown_category_removed"] += 1
             continue
        clean.append(r)

    if not clean:  # nothing survived validation: no intensities to test
        report["clean_rows"] = 0
        return [], dict(report)

    # outlier rule: litres per hectare above Q3 + 3*IQR is treated as an error
    intensities = sorted(r["water_used_m3"] / r["area_ha"] for r in clean)
    q1 = intensities[len(intensities) // 4]
    q3 = intensities[3 * len(intensities) // 4]
    limit = q3 + 3 * (q3 - q1)
    kept = []
    for r in clean:
        if r["water_used_m3"] / r["area_ha"] > limit:
            report["outliers_removed"] += 1
        else:

            kept.append(r)
    report["clean_rows"] = len(kept)
    return kept, dict(report)


def save_csv(records, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)


# ------------------------------------------------------------ analysis ----
def group_stats(records, key):
    """Total water, area, records and intensity (m3/ha) per group."""
    g = defaultdict(lambda: {"water": 0.0, "area": 0.0, "n": 0})
    for r in records:
        k = r[key]
        g[k]["water"] += r["water_used_m3"]
        g[k]["area"] += r["area_ha"]
        g[k]["n"] += 1
    total = sum(v["water"] for v in g.values())
    out = []
    for k, v in g.items():
        out.append({
             key: k,
             "records": v["n"],
             "total_m3": round(v["water"], 1),
             "share_pct": round(100 * v["water"] / total, 2),
             "area_ha": round(v["area"], 2),
             "m3_per_ha": round(v["water"] / v["area"], 1),
        })
    return sorted(out, key=lambda x: x["m3_per_ha"], reverse=True)


def monthly_stats(records):
    water = defaultdict(float)
    for r in records:
        water[r["month"]] += r["water_used_m3"]
    total = sum(water.values())
    return [{"month": MONTHS[m - 1], "total_m3": round(water[m], 1),
             "share_pct": round(100 * water[m] / total, 2)}
            for m in range(1, 13)]


def crop_region_matrix(records):
    cell = defaultdict(lambda: [0.0, 0.0])
    for r in records:
        c = cell[(r["crop"], r["region"])]
        c[0] += r["water_used_m3"]
        c[1] += r["area_ha"]
    return {k: round(v[0] / v[1], 1) for k, v in cell.items()}


def potential_saving(records, method_stats):
    """Estimate saving if Flood/Furrow/Sprinkler fields moved to drip at its observed rate."""
    drip = next((m["m3_per_ha"] for m in method_stats
                 if m["irrigation_method"] == "Drip"), None)
    return drip


# --------------------------------------------------------------- plots ----
def make_charts(crops, regions, months, matrix, methods):
    os.makedirs(OUT_DIR, exist_ok=True)
    green, blue, orange = "#2E7D32", "#1565C0", "#EF6C00"

    fig, ax = plt.subplots(figsize=(7, 4))
    names = [c["crop"] for c in crops]
    ax.bar(names, [c["m3_per_ha"] for c in crops], color=green)
    ax.set_ylabel("Water use (m³ per hectare)")
    ax.set_title("Water Intensity by Crop")
    plt.xticks(rotation=30)
    fig.tight_layout(); fig.savefig(f"{OUT_DIR}/crop_intensity.png", dpi=200); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([r["region"] for r in regions],
           [r["total_m3"] / 1000 for r in regions], color=blue)
    ax.set_ylabel("Total water used (thousand m³)")
    ax.set_title("Total Water Consumption by Region")
    plt.xticks(rotation=20)
    fig.tight_layout(); fig.savefig(f"{OUT_DIR}/region_total.png", dpi=200); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot([m["month"] for m in months],
            [m["total_m3"] / 1000 for m in months],
            marker="o", color=orange)
    ax.set_ylabel("Total water used (thousand m³)")
    ax.set_title("Monthly Water Consumption")
    ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(f"{OUT_DIR}/monthly_usage.png", dpi=200); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([m["irrigation_method"] for m in methods],
           [m["m3_per_ha"] for m in methods], color="#6A1B9A")
    ax.set_ylabel("Water use (m³ per hectare)")
    ax.set_title("Water Intensity by Irrigation Method")
    fig.tight_layout(); fig.savefig(f"{OUT_DIR}/method_intensity.png", dpi=200); plt.close(fig)

    crop_names = sorted({k[0] for k in matrix})
    reg_names = sorted({k[1] for k in matrix})
    grid = [[matrix.get((c, r), 0) for r in reg_names] for c in crop_names]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    im = ax.imshow(grid, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(reg_names))); ax.set_xticklabels(reg_names, rotation=25)
    ax.set_yticks(range(len(crop_names))); ax.set_yticklabels(crop_names)
    for i in range(len(crop_names)):
        for j in range(len(reg_names)):
            ax.text(j, i, f"{grid[i][j]:.0f}", ha="center", va="center", fontsize=7)
    ax.set_title("Crop x Region Water Intensity (m³/ha)")
    fig.colorbar(im, ax=ax)
    fig.tight_layout(); fig.savefig(f"{OUT_DIR}/heatmap.png", dpi=200); plt.close(fig)


# ---------------------------------------------------------------- main ----
def print_table(title, rows, cols):
    print(f"\n=== {title} ===")
    print(" | ".join(f"{c:>14}" for c in cols))
    for r in rows:
        print(" | ".join(f"{str(r[c]):>14}" for c in cols))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(RAW_FILE):
        n = generate_raw_data(RAW_FILE)
        print(f"Generated {n} raw irrigation records -> {RAW_FILE}")

    raw = load_csv(RAW_FILE)
    clean, report = clean_data(raw)
    save_csv(clean, CLEAN_FILE)

    print("\n=== DATA CLEANING REPORT ===")
    for k, v in report.items():
        print(f"{k:28s}: {v}")

    total_water = sum(r["water_used_m3"] for r in clean)
    total_area = sum(r["area_ha"] for r in clean)
    print(f"\nTotal water used : {total_water:,.1f} m3")
    print(f"Total area       : {total_area:,.2f} ha")
    print(f"Overall intensity: {total_water / total_area:,.1f} m3/ha")

    crops = group_stats(clean, "crop")
    regions = group_stats(clean, "region")
    methods = group_stats(clean, "irrigation_method")
    months = monthly_stats(clean)
    matrix = crop_region_matrix(clean)

    cols = ["records", "total_m3", "share_pct", "area_ha", "m3_per_ha"]
    print_table("CROPS (ranked by m3/ha)", crops, ["crop"] + cols)
    print_table("REGIONS (ranked by m3/ha)", regions, ["region"] + cols)
    print_table("IRRIGATION METHODS", methods, ["irrigation_method"] + cols)
    print_table("MONTHLY USAGE", months, ["month", "total_m3", "share_pct"])

    peak = sorted(months, key=lambda m: m["total_m3"], reverse=True)[:3]
    print("\nHigh-consumption months:", ", ".join(m["month"] for m in peak))
    print("Top 3 water-intensive crops:", ", ".join(c["crop"] for c in crops[:3]))
    print("Highest-intensity region   :", regions[0]["region"])
    print("Lowest-intensity region    :", regions[-1]["region"])

    # simple saving estimate: shift Flood fields to the drip rate
    drip = potential_saving(clean, methods)
    flood = next((m for m in methods if m["irrigation_method"] == "Flood"), None)
    if drip and flood:
        # compare like with like is not possible across crops, so apply a
        # conservative 30% reduction on Flood water as the planning figure
        saving = flood["total_m3"] * 0.30
        print(f"\nConservative saving (30% of flood water): {saving:,.1f} m3 "
              f"= {100 * saving / total_water:.1f}% of total use")

    print("\n=== RECOMMENDATIONS ===")
    print("1. Move Rice/Sugarcane from flood to AWD / drip where feasible.")
    print("2. Schedule irrigation at night/early morning in peak months.")
    print("3. Use mulching and soil-moisture sensors to avoid over-irrigation.")
    print("4. Shift high-intensity regions toward lower-water crops (maize, pulses).")
    print("5. Install flow meters per farm and review monthly.")

    make_charts(crops, regions, months, matrix, methods)
    for name, data in (("crop", crops), ("region", regions),
                       ("method", methods), ("month", months)):

        save_csv(data, f"{OUT_DIR}/summary_{name}.csv")
    print(f"\nCharts and summary tables saved in ./{OUT_DIR}/")


if __name__ == "__main__":
    main()
