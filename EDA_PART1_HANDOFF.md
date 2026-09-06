# Group018 EDA: first contribution

Completed for Zaheer Imad Ul Haq using the existing solution notebook's conventions:
descriptive variable names, short documented helpers, explicit calculations, visible
checks, and "Observation and decision" explanations.

## Completed work

| Item | Contents |
|---|---|
| `Group018_EDA.ipynb` | Shared loading/configuration, context and preparation assurance, Figures 1-3, Findings 1-5, MLQ-1 and MLQ-2, and limitations for this contribution. Executed outputs are included. |
| `eda_figures/Group018_Figure1_order_totals.png` | Full distribution of completed-order totals, with mean and median. |
| `eda_figures/Group018_Figure2_product_revenue.png` | Top ten products by gross item revenue, using a checked item-to-product join. |
| `eda_figures/Group018_Figure3_weekly_orders.png` | Monday-to-Sunday order counts, with the partial boundary week shown separately. |
| `requirements.txt` | Tested Python dependencies for the existing solution and new EDA notebook. |

The original template, solution files, mapping and all six standardised CSVs are
unchanged. The source snapshot was repository commit `a2a7d28`.

## Run the notebook

1. Open the repository folder in VS Code with Jupyter support, or in an existing
   Jupyter installation. The notebook was tested with Python 3.12.13.
2. Install the declared dependencies in your Python environment:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Open `Group018_EDA.ipynb`, select that environment and run **Restart and Run All**.
4. Confirm the final EDA register reports no failed checks. Images are recreated in
   `eda_figures/`; no helper columns or new CSVs are written to `outputs/`.

The first contribution was executed top to bottom in a fresh in-process IPython
kernel: **18 code cells, zero execution errors, three embedded figures and 29
passing EDA checks**. An in-process kernel was used because the verification host
does not permit socket binding. All three saved chart images were visually checked.
These execution checks are separate from the 61 upstream Task 4 checks cited in
the notebook; the upstream parsing and cleaning pipeline was not rerun.

## Verified results to understand

- Figure 1 uses 5,000 completed AUD orders. The mean order total is AUD 2,804.05;
  the median is approximately AUD 2,371.01. There are 150 orders above the upper
  1.5-IQR fence. They are retained because unusual size does not establish error.
- Figure 2 preserves all 15,618 item rows and AUD 15,457,463.98 gross item revenue
  through the product join. The top ten of 1,000 sold products contribute 4.04% of
  that total. Revenue is before coupons, including GST and excluding delivery;
  it is not the same measure as Figure 1's order total and is not profit.
- Figure 3 contains 52 complete calendar weeks with 4,982 orders, averaging 95.81
  per week. The bin starting 31 December 2018 has 18 orders but just one calendar
  date in the observed window. It is excluded from full-week averages and extrema.

These are snapshot results. Re-running the notebook recalculates its charts,
statistics and narrative outputs from the six CSVs.

## Exact teammate starting point

Start at **"Teammate continuation: Figures 4-6"** in the notebook. Run the shared
configuration and loading cells first. Add your figure sections at this location.

| Figure | Responsibility | Data and denominator |
|---|---|---|
| 4 | Review/text behaviour: review language counts and percentages. | `product_reviews.language_code`; one canonical review per observation. |
| 5 | Operational performance: late-delivery percentage across order-value groups. | Join `deliveries` to `orders` on `order_id`. Check cardinality, match coverage and row-count preservation. Use standardised `delay_days > 0`, and report eligible deliveries in each group. |
| 6 | Multivariate relationship: review length by rating, split by non-Latin-script status. | `product_reviews.rating`, `review_length_chars` and `contains_non_latin_script`. Report group sizes and any sentinel exclusions. |

This order preserves the team's agreed split. The supplied template initially
places the temporal category at Figure 4; the category has deliberately moved to
Figure 3 here. The assignment requires category coverage, not that template order.

For each new figure provide the question, observation unit, denominator, tables and
join keys, readable chart labels, numerical interpretation and a material limitation.
Use `record_eda_check` for relevant join checks. Add the new PNG filenames to the
final export-check list once the figures are implemented.

After your figures, add **Findings 6-10** and **MLQ-3 to MLQ-5** in the corresponding
sections, and finish the combined limitations and conclusion. ML questions need a
business decision, unit, target/objective, decision-time predictors, validation split,
metric and leakage/deployment risks. Do not train models in this assignment.

Figures 1-3 use three tables and one relational analysis. After the proposed
remaining analyses are completed, the six figures will use five tables and two
relational analyses while covering all six required categories. Do not describe
the entire assessment as complete until the second contribution has been added.

## Final team assembly

- Remove interim contribution-status and handoff wording from the final assessed
  report; include the full group's names and student IDs where required.
- Produce `Group018_EDA.pdf` with at most ten assessed pages. Use concise prose and
  readable figures; do not print the entire code notebook as the report.
- Keep exactly ten numbered findings and five numbered ML questions in the final
  combined submission. The first contribution already supplies five and two.
- Include this AI-assisted work in the signed group declaration and complete
  assignment conversation records required by the specification.
- Submit the EDA PDF separately from the assignment ZIP. The complete notebook
  belongs in the ZIP. Do not submit the supplied raw JSON/XML data.

No commit or push was made while preparing this contribution. The user requested
review and explicit permission before pushing to their fork.
