# Experiment Audit Workbench

A small, dependency-free audit for individually randomized, two-arm experiments with binary outcomes. The included fictional experiment asks whether a reminder changes completion. Most observed participants in one arm can appear to perform better simply because the outcomes of non-completers are less likely to get recorded.

## Quick start

Python 3.10+; no installation or network required.

```sh
python workbench.py assignments.csv outcomes.csv --output report.json
python -m unittest -v
```

The report should say **hold**. The observed treatment group looks better, but differential missingness means the all-assigned effect could favor either arm. Run `python make_demo.py` to regenerate the fictional data.

## Input contracts

- `assignments.csv`: one row per assigned unit, with `unit,arm,stratum`; arm must be `control` or `treatment`. A unit should be the independent randomization unit.
- `outcomes.csv`: one row per unit with a measured binary outcome, with `unit,outcome`. A unit with no outcome has **no row**. A measured zero is distinct from a missing row.
- `--target-treatment` specifies the preregistered allocation share, not the share among observed units.

## What the report audits

1. Fail on malformed units, duplicate assignments/outcomes, unsupported arms, nonbinary outcomes, or outcomes with no assignment.
2. Check the planned allocation against assignment counts with a two-sided normal approximation; suspend the check for small expected counts.
3. Count assigned, observed, and successful units in each arm, and flag a large difference in attrition.
4. Show the observed-only risk difference with an approximate Wald interval when both arms have at least ten successes and ten failures. Separately, show worst-case all-assigned effect bounds without assumptions about missing outcomes.
5. Provide exploratory strata and hashes of both inputs. These strata are not multiplicity-adjusted hypothesis tests.

## Limitations

This audit does not prove randomization, establish causal identification under missingness, adjust for clusters, monitor repeated peeks, or handle time-to-event outcomes. A complete-case confidence interval does not account for missingness bias. The worst-case bounds are logical bounds, not confidence intervals. A reviewable report does not imply a successful intervention. No actual participant data or clinical conclusions are included.
