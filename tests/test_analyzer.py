"""Unit + integration tests for water_usage_analyzer.py (stdlib unittest).

Run from the project root:  python -m unittest discover -s tests -v
"""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import water_usage_analyzer as w


def row(**kw):
    base = {"record_id": "1", "farm_id": "F100", "region": "Warangal",
            "crop": "Rice", "month": "10", "area_ha": "2.0",
            "irrigation_method": "Flood", "water_used_m3": "2000.0"}
    base.update(kw)
    return base


def cleaned(rows):
    clean, _ = w.clean_data(rows)
    return clean


class TestCleanData(unittest.TestCase):
    def test_normal_row_kept_and_typed(self):
        clean, rep = w.clean_data([row()])
        self.assertEqual(len(clean), 1)
        self.assertIsInstance(clean[0]["area_ha"], float)
        self.assertEqual(clean[0]["month"], 10)

    def test_text_normalised(self):
        clean, _ = w.clean_data([row(crop=" rice ", region=" warangal ",
                                     irrigation_method=" flood ")])
        self.assertEqual(clean[0]["crop"], "Rice")
        self.assertEqual(clean[0]["region"], "Warangal")

    def test_exact_duplicate_removed(self):
        _, rep = w.clean_data([row(), row()])
        self.assertEqual(rep["duplicates_removed"], 1)
        self.assertEqual(rep["clean_rows"], 1)

    def test_missing_negative_invalid_month_unknown(self):
        rows = [row(record_id="2", area_ha=""),
                row(record_id="3", water_used_m3="-50"),
                row(record_id="4", month="13"),
                row(record_id="5", crop="Banana")]
        _, rep = w.clean_data(rows)
        self.assertEqual(rep["missing_values_removed"], 1)
        self.assertEqual(rep["negative_or_zero_removed"], 1)
        self.assertEqual(rep["invalid_month_removed"], 1)
        self.assertEqual(rep["unknown_category_removed"], 1)
        self.assertEqual(rep["clean_rows"], 0)

    def test_non_numeric_removed(self):
        _, rep = w.clean_data([row(area_ha="abc")])
        self.assertEqual(rep["non_numeric_removed"], 1)

    def test_outlier_rule(self):
        # 20 ordinary rows + one extreme row: Q3 + 3*IQR must drop it
        rows = [row(record_id=str(i), water_used_m3="1000.0")
                for i in range(20)]
        rows.append(row(record_id="99", water_used_m3="250000.0"))
        _, rep = w.clean_data(rows)
        self.assertEqual(rep["outliers_removed"], 1)
        self.assertEqual(rep["clean_rows"], 20)


class TestStats(unittest.TestCase):
    def test_group_stats_intensity_and_ranking(self):
        rows = [row(crop="Rice", area_ha="2.0", water_used_m3="2000.0"),
                row(crop="Maize", area_ha="4.0", water_used_m3="1000.0")]
        stats = w.group_stats(cleaned(rows), "crop")
        self.assertEqual(stats[0]["crop"], "Rice")  # 1000 m3/ha > 250
        self.assertEqual(stats[0]["m3_per_ha"], 1000.0)
        self.assertAlmostEqual(stats[0]["share_pct"] + stats[1]["share_pct"],
                               100.0, places=1)

    def test_monthly_shares(self):
        rows = [row(month="1", water_used_m3="1000.0"),
                row(month="10", water_used_m3="3000.0")]
        months = w.monthly_stats(cleaned(rows))
        self.assertEqual(len(months), 12)
        self.assertEqual(months[0]["share_pct"], 25.0)
        self.assertEqual(months[9]["share_pct"], 75.0)

    def test_crop_region_matrix(self):
        rows = [row(crop="Rice", region="Warangal", area_ha="2.0",
                    water_used_m3="2000.0")]
        self.assertEqual(w.crop_region_matrix(cleaned(rows))[("Rice", "Warangal")],
                         1000.0)

    def test_potential_saving_returns_drip_rate(self):
        methods = [{"irrigation_method": "Drip", "m3_per_ha": 485.6},
                   {"irrigation_method": "Flood", "m3_per_ha": 1365.0}]
        self.assertEqual(w.potential_saving([], methods), 485.6)


class TestGenerationAndEndToEnd(unittest.TestCase):
    def test_generate_is_deterministic_and_has_612_rows(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "raw.csv")
            n = w.generate_raw_data(path, seed=16)
            self.assertEqual(n, 612)  # 600 base + 12 injected duplicates
            rows = w.load_csv(path)
            clean, rep = w.clean_data(rows)
            self.assertEqual(rep["clean_rows"], 550)

    def test_main_produces_outputs(self):
        # Run the real program in a fresh temp directory.
        import shutil
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(os.path.join(here, "water_usage_analyzer.py"), d)
            r = subprocess.run([sys.executable, "water_usage_analyzer.py"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("clean_rows", r.stdout)
            self.assertIn("1,292,341.0", r.stdout)
            for f in ("crop_intensity.png", "region_total.png",
                      "monthly_usage.png", "method_intensity.png",
                      "heatmap.png"):
                self.assertTrue(os.path.exists(os.path.join(d, "output", f)),
                                f)
            self.assertTrue(os.path.exists(
                os.path.join(d, "irrigation_records_clean.csv")))


if __name__ == "__main__":
    unittest.main()
