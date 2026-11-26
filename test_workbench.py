import tempfile
import unittest
from pathlib import Path

from make_demo import write_demo
from workbench import audit


class ExperimentTest(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_demo(root)
            self.a = (root / "assignments.csv").read_bytes()
            self.y = (root / "outcomes.csv").read_bytes()

    def test_demo_exposes_biased_observed_comparison(self):
        report = audit(self.a, self.y)
        self.assertEqual(report["status"], "hold")
        self.assertGreater(report["contrast"]["complete_case_difference"], .10)
        self.assertIn("differential_attrition", report["flags"])
        self.assertIn("direction_not_robust_to_missing_outcomes", report["flags"])
        self.assertEqual(report["allocation"]["approximate_p"], 1)
        low, high = report["contrast"]["missing_outcome_bounds"]
        self.assertLess(low, 0)
        self.assertGreater(high, 0)

    def test_complete_balanced_data_has_identical_bounds(self):
        y = ("unit,outcome\n" + "".join(f"U{i:04},{int(i % 5 == 0)}\n" for i in range(440))).encode()
        report = audit(self.a, y)
        self.assertEqual(report["status"], "reviewable")
        d = report["contrast"]["complete_case_difference"]
        self.assertEqual(report["contrast"]["missing_outcome_bounds"], [d, d])

    def test_expected_assignment_ratio_is_used(self):
        self.assertIn("sample_ratio_mismatch", audit(self.a, self.y, target=.75)["flags"])

    def test_duplicate_assignment_is_rejected(self):
        with self.assertRaises(ValueError):
            audit(self.a + b"U0000,control,new\n", self.y)

    def test_orphan_outcome_is_rejected(self):
        with self.assertRaises(ValueError):
            audit(self.a, self.y + b"U9940,1\n")

    def test_incomplete_arm_is_invalid(self):
        with self.assertRaises(ValueError):
            audit(b"unit,arm,stratum\na,control,new\n", b"unit,outcome\na,1\n")


if __name__ == "__main__":
    unittest.main()
