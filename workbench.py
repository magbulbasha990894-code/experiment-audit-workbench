"""Audit a two-arm experiment using assigned units and observed outcomes."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def read_csv(raw, required):
    reader = csv.DictReader(raw.decode("utf-8-sig").splitlines())
    if not reader.fieldnames or not required <= set(reader.fieldnames):
        raise ValueError(f"required columns: {', '.join(sorted(required))}")
    result = {}
    for line, row in enumerate(reader, 2):
        uid = row.get("unit", "")
        if not uid or uid in result or None in row or any(row.get(key) in (None, "") for key in required):
            raise ValueError(f"blank, duplicate, or malformed unit on line {line}")
        result[uid] = row
    return result


def summarize(groups):
    return {arm: {"assigned": len(rows), "observed": sum(y is not None for y in rows),
                  "success": sum(y == 1 for y in rows)}
            for arm, rows in groups.items()}


def contrast(counts):
    c, t = (counts[a] for a in ("control", "treatment"))
    if min(c["assigned"], t["assigned"]) == 0:
        return None
    # All-assigned binary-outcome bounds, with missing outcomes allowed to differ by arm.
    cmin = c["success"] / c["assigned"]
    cmax = (c["success"] + c["assigned"] - c["observed"]) / c["assigned"]
    tmin = t["success"] / t["assigned"]
    tmax = (t["success"] + t["assigned"] - t["observed"]) / t["assigned"]
    result = {"missing_outcome_bounds": [tmin - cmax, tmax - cmin]}
    if min(c["observed"], t["observed"]) > 0:
        pc, pt = (a["success"] / a["observed"] for a in (c, t))
        d = pt - pc
        # Report Wald CI only if each arm has enough observed successes and failures.
        enough = all(min(a["success"], a["observed"] - a["success"]) >= 10 for a in (c, t))
        radius = 1.96 * math.sqrt(pt * (1 - pt) / t["observed"] + pc * (1 - pc) / c["observed"])
        result.update(complete_case_difference=d,
                      complete_case_95=[max(-1, d-radius), min(1, d+radius)] if enough else None)
    return result


def audit(assignments, outcomes, target=.5, attrition_limit=.05, alpha=.01):
    if not 0 < target < 1 or not 0 <= attrition_limit <= 1 or not 0 < alpha < 1:
        raise ValueError("invalid audit parameters")
    assigned = read_csv(assignments, {"unit", "arm", "stratum"})
    observed = read_csv(outcomes, {"unit", "outcome"})
    if not assigned or observed.keys() - assigned.keys():
        raise ValueError("no assignments or outcomes for unassigned units")
    if any(v["arm"] not in {"control", "treatment"} for v in assigned.values()):
        raise ValueError("unsupported arm")
    if any(v["outcome"] not in {"0", "1"} for v in observed.values()):
        raise ValueError("outcome must be 0 or 1")
    overall = {"control": [], "treatment": []}
    groups = {}
    for uid, row in assigned.items():
        result = int(observed[uid]["outcome"]) if uid in observed else None
        arm = row["arm"]
        overall[arm].append(result)
        groups.setdefault(row["stratum"], {"control": [], "treatment": []})[arm].append(result)
    counts = summarize(overall)
    if any(c["assigned"] == 0 for c in counts.values()):
        raise ValueError("both arms must have assigned units")
    n = len(assigned)
    t = counts["treatment"]["assigned"]
    z = (t - n * target) / math.sqrt(n * target * (1 - target))
    srm = math.erfc(abs(z) / math.sqrt(2)) if min(n * target, n * (1-target)) >= 10 else None
    for row in counts.values():
        row["attrition"] = 1 - row["observed"] / row["assigned"]
    delta = abs(counts["control"]["attrition"] - counts["treatment"]["attrition"])
    flags = []
    if srm is None:
        flags.append("too_few_assignments_for_balance_check")
    elif srm < alpha:
        flags.append("sample_ratio_mismatch")
    if delta > attrition_limit and not math.isclose(delta, attrition_limit):
        flags.append("differential_attrition")
    comparisons = contrast(counts)
    low, high = comparisons["missing_outcome_bounds"]
    if low <= 0 <= high and len(observed) < n:
        flags.append("direction_not_robust_to_missing_outcomes")
    if any(not row["observed"] for row in counts.values()):
        flags.append("no_outcomes_in_one_arm")
    strata = {}
    for name, rows in sorted(groups.items()):
        sc = summarize(rows)
        strata[name] = {"counts": sc, "contrast": contrast(sc)}
    return {"status": "hold" if flags else "reviewable", "flags": flags,
            "allocation": {"target_treatment_share": target, "observed_treatment_share": t / n,
                           "approximate_p": srm, "alpha": alpha},
            "counts": counts, "absolute_attrition_gap": delta, "attrition_gap_limit": attrition_limit,
            "contrast": comparisons, "strata_exploratory": strata,
            "inputs_sha256": {name: hashlib.sha256(content).hexdigest()
                             for name, content in {"assignments": assignments, "outcomes": outcomes}.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assignments", type=Path)
    parser.add_argument("outcomes", type=Path)
    parser.add_argument("--target-treatment", type=float, default=.5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = json.dumps(audit(args.assignments.read_bytes(), args.outcomes.read_bytes(),
                                  args.target_treatment), indent=2) + "\n"
        if args.output:
            args.output.write_text(result, encoding="utf-8", newline="\n")
        else:
            print(result, end="")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
