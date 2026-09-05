# Task 5 Handoff

## Use the completed work

Read the completed Task 1 to Task 4 work before starting any analysis.

Treat the six exported CSVs in `outputs/` as the finished, validated data source. Do not re-derive, re-clean or re-transform any field.

Do not rerun the solution notebook's parsing or cleaning pipeline inside the EDA notebook. Load the six CSVs directly with `pandas.read_csv`.

Load every CSV with `keep_default_na=False` so the literal `NaN` sentinel stays visible as text rather than being converted to a missing value.

Reuse the stable `MAP-...` IDs from `Group018_source_to_target_mapping.csv` and the stable `VAL-...` IDs from the Task 4 validation register when citing evidence; do not repeat the complete mapping or the complete validation register inside the report.

## Set up the EDA notebook

Rename `A1_EDA_template.ipynb` to `Group018_EDA.ipynb`.

Set `GROUP_ID = "Group018"` and `OUTPUT_DIR = Path("outputs")` in the configuration cell.

Keep the path configurable and relative; do not hard-code a student-specific absolute path.

Remove unused template prompts and instructional text before the final export.

## Build the assessed visualisations

Produce 6 to 8 clearly labelled assessed visualisations, numbered `Figure 1`, `Figure 2`, and so on. Only the first eight are marked.

Across the full set, cover all six required categories at least once: univariate distribution or composition; bivariate relationship or group comparison; multivariate or segmented relationship; temporal pattern; review or text behaviour; and delivery or operational performance in relation to an order, customer, product or review characteristic.

Across the full set, use evidence from at least four of the six output tables.

Across the full set, include at least two visualisations that correctly join related tables.

One visualisation may satisfy more than one category only when the analytical question genuinely spans both; do not force this artificially.

A coordinated set of subplots answering one shared question counts as one visualisation, not several.

For every assessed visualisation, state: the analytical question; the observation unit and denominator; the tables and join keys used; a chart type appropriate to the variables and comparison; readable titles, axes, legends and units; and an explanation of the result together with one material limitation.

Before reporting any metric derived from a join across one-to-many tables, check for accidental row multiplication (for example, comparing a row count or a sum before and after the join) and show that check.

Calculate every metric at its intended grain; do not silently inflate an order-, customer-, or product-level metric by joining in a one-to-many table without first aggregating.

## Write the ten findings

Write exactly ten numbered findings, no more and no fewer counted toward marking.

For each finding, cite the supporting assessed figure or a reported statistic.

For each finding, state: what was observed and at what grain; the magnitude, denominator or sample size; why it may matter in the retail context; a plausible alternative explanation or source of uncertainty; and a proportionate implication, next investigation or recommendation.

Do not claim causation from an observed association without a defensible design; a finding that a relationship is weak, uncertain or not decision-relevant can still be a high-quality finding when the evidence supports that conclusion.

## Write the five ML questions

Write exactly five numbered machine-learning questions grounded in the EDA findings above.

Across the five questions, cover at least two different problem types (for example classification, regression, clustering, anomaly detection or forecasting).

For each question, specify: the business decision or use case; the prediction or analysis unit; the target or unsupervised objective; candidate predictors that are genuinely available at decision time; an appropriate validation split; at least one evaluation metric; and likely target leakage, temporal leakage, fairness or deployment risks.

Keep each question to approximately 80-120 words, or present it as one compact table, following the `MLQ-...` structure in the template.

Do not train, tune or compare any model; Task 5 requires the question design only.

## Assemble the report

Export the completed notebook content into `Group018_EDA.pdf`, no more than ten assessed pages from the introduction through the conclusion; the cover page, contents page and references are excluded from that limit.

Follow this structure: problem context and data scope; data-preparation assurance; the 6-8 assessed visualisations; the ten numbered findings; the five numbered ML questions; limitations; and a conclusion.

In the data-preparation assurance section, communicate approximately 3-5 material transformation decisions and 4-6 material validation results, citing the relevant `MAP-...` and `VAL-...` IDs rather than reproducing the full artifacts.

Do not include code listings in the report unless a short expression is genuinely necessary to explain an assessed decision.

Keep every table and figure readable at 100% zoom.

Cite external facts, code, data or ideas with one consistent referencing style throughout.

## Finalise

Confirm the EDA notebook reproduces every assessed figure and reported statistic purely from the six submitted CSVs, without depending on a different, hidden cleaning step.

Restart the kernel and run every cell from top to bottom before treating any figure or statistic as final.

Do not place `Group018_EDA.pdf` inside the submission ZIP; it is submitted as a separate top-level file alongside `Group018_A1_submission.zip`.

Keep all work on `master` and create no commit unless a later instruction explicitly requests one.
