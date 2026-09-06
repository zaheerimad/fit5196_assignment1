# EDA handoff

Figures 1-3, Findings 1-5 and MLQ-1 to MLQ-2 are in `Group018_EDA.ipynb`.
Charts are saved in `eda_figures/`.

## Run

Open the notebook from the repository root and select **Restart and Run All**.
Install dependencies if needed:

```bash
python -m pip install -r requirements.txt
```

The notebook reads the six CSVs in `outputs/`. Keep `keep_default_na=False`
when loading them, and keep analysis columns inside the notebook.

## Continue with Figure 4

Add the remaining charts under **Figures 4-6** in the notebook.

| Figure | Analysis | Tables |
|---|---|---|
| 4 | Review language counts and percentages | `product_reviews.language_code` |
| 5 | Late-delivery percentage by order-value group | Join `deliveries` to `orders` on `order_id`; use `delay_days > 0` |
| 6 | Review length by rating, split by non-Latin-script status | `product_reviews`: `rating`, `review_length_chars`, `contains_non_latin_script` |

For each chart, include the question, observation unit, denominator, join keys,
interpretation and a limitation. Check that joins preserve row counts and totals.
Add new image filenames to `figure_filenames` in the final notebook cell.

Then add Findings 6-10, MLQ-3 to MLQ-5, and the final conclusion. The full set
needs 6-8 figures, exactly 10 findings and 5 ML questions. Do not train models.

## Points to keep consistent

- Figure 2 uses gross item revenue before coupons and excluding delivery charges.
  Figure 1 uses order totals after discounts and including delivery charges.
- The week starting 31 December 2018 contains one day of data. It is excluded
  from full-week averages and comparisons.
- The planned six figures cover five tables and two relational analyses.
- Keep `Group018_EDA.pdf` within ten assessed pages and submit it separately
  from the ZIP.
