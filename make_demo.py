"""Generate a fictional reminders experiment with outcome missingness."""
import csv
from pathlib import Path
from random import Random


def write_demo(root):
    rng = Random(413)
    with ((root / "assignments.csv").open("w", newline="", encoding="utf-8") as handle_a,
          (root / "outcomes.csv").open("w", newline="", encoding="utf-8") as handle_y):
        assignments, outcomes = csv.writer(handle_a), csv.writer(handle_y)
        assignments.writerow(("unit", "arm", "stratum"))
        outcomes.writerow(("unit", "outcome"))
        for i in range(440):
            arm = "treatment" if i % 2 else "control"
            stratum = "new" if i % 4 < 2 else "returning"
            # Pair the fictional potential outcome to make the true effect zero.
            if i % 2 == 0:
                outcome = rng.random() < (.53 if stratum == "returning" else .32)
            # Outcome-dependent tracking loss makes the observed-only comparison misleading.
            missing_probability = .60 if arm == "treatment" and not outcome else .03
            assignments.writerow((f"U{i:04}", arm, stratum))
            if rng.random() >= missing_probability:
                outcomes.writerow((f"U{i:04}", int(outcome)))


if __name__ == "__main__":
    write_demo(Path(__file__).parent)

