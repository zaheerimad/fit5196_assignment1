# Task 3 and Task 4 - Text Processing and Validation

## Task 3: Regex and Multilingual Text Processing

### Purpose

Task 3 was completed by treating the assignment specification's published text-processing order, the marking rubric's D1-D3 criteria, and the supplied public test cases as the ultimate sources of truth. The completed Task 1 profiling, mapping, and Task 2 relational transformation were treated as finished and were not altered.

The six required functions were implemented in a single, dependency-free module so they could be imported and tested independently of the notebook. Each function was verified against isolated test strings first, then re-verified against real raw review text sampled directly from the allocated package, since correct behaviour on a handful of invented examples does not guarantee correct behaviour once applied across the full seven-thousand-row dataset.

### Files used

- `Group018_text_functions.py` (created)
- `Group018_solution.ipynb` (Task 3 section added after the Task 2 conclusion)
- `templates/A1_public_text_test_cases.csv`
- The four raw narrative columns already retained by Task 2's staging DataFrames without being exported: `orders_stage["customer_note_raw"]`, `deliveries_stage["delivery_note_raw"]`, `products_stage["product_description_raw"]`, `product_reviews_stage["review_text_raw"]`

### Steps taken and reasons

#### 1. The six required functions were implemented

`clean_narrative_text`, `extract_order_reference`, `extract_product_sku`, `extract_promo_code`, `build_latin_analysis`, and `contains_non_latin_script` were implemented in `Group018_text_functions.py`, following the published processing order: extract references from the raw value before cleaning; decode HTML entities and apply Unicode NFC normalisation; strip tags, markers, URLs and emoji; strip the reference and promotion wrappers; collapse whitespace and lower-case; and return the literal string `NaN` when nothing readable remains. This was done because the six functions must be independently importable and testable, with no file I/O, network access or row-specific lookups inside them.

#### 2. Emoji removal was corrected against real characters

An initial emoji Unicode-range set missed the plain star character (U+2B50, Miscellaneous Symbols and Arrows block) and the watch/hourglass block (U+2300-23FF). This was found by inspecting real cleaned review output rather than assuming a standard emoji range list was complete. Both ranges were added to the removal pattern.

#### 3. Non-Latin combining marks were found to leak into the Latin-analysis field

Arabic harakat and Devanagari vowel signs are not classified as letters by Python's `str.isalpha()`, so an early version of `build_latin_analysis` retained them by mistake, alongside legitimate punctuation. This was corrected by dropping any character whose Unicode category begins with `M` (a combining mark) unless it belongs to a short list of common non-ASCII "smart" punctuation marks (curly quotes, en/em dash, ellipsis).

#### 4. Non-Latin, script-specific punctuation was found to leak similarly

Chinese and Japanese full-width punctuation is not a combining mark, so the correction above did not remove it. The rule was generalised: any non-ASCII character is dropped from the Latin-analysis field unless it is a Latin letter or one of the smart-punctuation exceptions, which covers both this case and the combining-mark case with one rule.

#### 5. Orphaned punctuation was found once non-Latin words were removed

After non-Latin letters were stripped from a foreign-language sentence, that sentence's own ASCII commas and periods sometimes remained as meaningless standalone tokens. A post-processing step now drops any whitespace-separated token containing no letter and no digit, while leaving punctuation still attached to a surviving word untouched.

#### 6. The reference-wrapper regex was corrected against real raw review text

The initial pattern for removing the `Reference: ... | SKU: ...` wrapper assumed a punctuation separator (pipe, semicolon or slash) was always present. Real raw review text sometimes uses only a bare newline or tab as the separator. The separator character class was widened to include whitespace, and the correction was verified against five real raw review rows sampled directly from `product_reviews_stage["review_text_raw"]`.

#### 7. The SKU boundary rule was tightened using the supplied public test cases

Running the official `A1_public_text_test_cases.csv` (eighteen cases) surfaced one failure: `SKU-ABC123-extra` was being truncated to the valid-looking prefix `SKU-ABC123` rather than being rejected as a malformed extension. A negative lookahead was added so a SKU match immediately followed by a hyphen is rejected, in line with the published rule against accepting malformed near-matches.

#### 8. The eleven deferred fields were derived and inserted at their public-dictionary positions

`orders.customer_note_clean` and `orders.promo_code` were derived from `orders_stage["customer_note_raw"]`; `deliveries.delivery_note_clean` from `deliveries_stage["delivery_note_raw"]`; `products.product_description_clean` from `products_stage["product_description_raw"]`; and the seven `product_reviews` fields from `product_reviews_stage["review_text_raw"]`. Reference and SKU extraction were performed on the raw value before cleaning; Latin analysis was built from the cleaned value. Extra care was taken with `review_length_chars` and `review_word_count`, which are set to `0` rather than a missing value when the underlying review is the literal `NaN` sentinel, since both fields are declared non-nullable numeric fields in the public dictionary.

#### 9. Public and student-designed tests were run inside the notebook

All eighteen supplied public test cases and thirty-one additional student-designed cases -- covering matched, unmatched, missing, multilingual and near-match inputs across all six functions -- were run as executable, pass/fail-recorded checks, following the same register pattern already used for Task 2 verification.

#### 10. The complete workflow was re-run from a clean kernel

The notebook was restarted and run top to bottom, including Task 1 and Task 2, to confirm the eleven deferred fields, the test registers and the six-CSV export all reproduce correctly without depending on state left over from earlier debugging.

### Important decisions

Genuinely orphaned punctuation -- a standalone comma or period left behind once its associated non-Latin word was removed -- is dropped from `review_body_latin_analysis`, since it carries no analytical content; punctuation still attached to a surviving word is always preserved.

Non-ASCII "smart" punctuation common in ordinary Latin-script text (curly quotes, em/en dash, ellipsis) is retained rather than treated as script-specific noise.

`promo_code` returns the literal string `NaN` when absent, matching the source-to-target mapping's explicit transformation rule for `MAP-orders-23`, even though the public data dictionary marks the field `nullable = True`; this was confirmed against the completed mapping rather than assumed from the dictionary alone.

`review_length_chars` and `review_word_count` are set to `0`, not a missing value, for a review whose cleaned text is the literal `NaN` sentinel, since both fields are declared `nullable = False`.

## Task 4: Validation Register

### Purpose

Task 4 was completed by treating the specification's minimum required check areas and the official solution template's validation-register structure (`VAL-SCHEMA-`, `VAL-PK-`, `VAL-FK-`, `VAL-FLOW-`, `VAL-ARITH-`, `VAL-TIME-`, `VAL-TEXT-`) as the governing contract. The completed Task 2 interim verification (`task2_check_rows`) was treated as evidence of the interim, 100-field tables only; Task 4 builds a separate, complete register over the final, 111-field tables produced at the end of Task 3.

### Files used

No new files were created. The validation register was added directly to `Group018_solution.ipynb`, reusing objects already built earlier in the notebook: `final_tables`, `public_dictionary`, `task2_tables`, `order_conflicts`, `review_conflicts`, `orders_stage`, and `order_items_table`.

### Steps taken and reasons

#### 1. The register was scoped to the final tables, not the Task 2 interim ones

A new section and a fresh `val_check_rows` register were created after the Task 3 conclusion, rather than extending `task2_check_rows`, so the Task 2 interim evidence and the Task 4 final evidence remain independently readable.

#### 2. Schema checks were built directly from the public data dictionary

For each of the six tables, the exported column list and order were checked against `public_dictionary`, and every field marked `nullable = False` was checked for true blank values, distinguishing an empty Python/pandas value from the permitted literal `NaN` sentinel.

#### 3. Primary- and foreign-key checks covered all eight required relationships

Each table's declared primary key was checked for completeness and uniqueness. All eight foreign-key relationships listed in the specification were checked by confirming every non-null child value exists in the corresponding parent key set.

#### 4. Categorical and numeric range checks were added as a plausibility layer

Declared categorical fields (for example `order_status`, `loyalty_tier`) were checked for a small, bounded number of distinct values rather than free text, and numeric fields with an obvious plausible range (for example `rating` between 1 and 5) were checked for out-of-range values, without hard-coding the exact certified value list.

#### 5. Row-flow checks confirmed Task 3 did not silently change row counts

Each final table's row count was compared against the corresponding Task 2 interim table, and the previously computed `order_conflicts` and `review_conflicts` were re-checked for emptiness, so overlap handling remains verified after the Task 3 additions.

#### 6. Arithmetic checks reused Task 2's differences and added two independent recomputations

The `order_price_difference`, `tax_amount_difference` and `order_total_difference` columns already computed during Task 2 were turned into named, tolerance-based checks. Two further checks independently recomputed `order_price` from `order_items.line_revenue` and confirmed `tax_amount` equals `order_price / 11` without being added again into `order_total`.

#### 7. Temporal checks required parsing stored string dates only at check time

An initial version of the temporal checks assumed `order_timestamp`, `dispatch_date`, `delivered_date` and `review_timestamp` were already parsed datetime values. Running the checks against the real notebook raised an `AttributeError`, confirming these fields are correctly kept as export-format strings in the table objects, consistent with the practice already established during Task 2. The checks were corrected to call `pandas.to_datetime` on a copy of each field immediately before comparison, leaving the stored table columns untouched.

#### 8. Text and multilingual checks validated the final exported data, not the functions in isolation

Rather than repeating the Task 3 function-level tests, the final `product_reviews` table was checked directly: that extracted references are never a true blank, that `contains_non_latin_script` shows genuine variation across the dataset, and that a Latin-analysis field actually differs from the clean text whenever non-Latin script is flagged as present.

#### 9. The register was verified to genuinely detect problems, not just pass by default

A deliberate, temporary foreign-key violation and a deliberate monetary discrepancy were injected into copies of the final tables outside the notebook, confirming the relevant checks correctly reported a failure, before the register was trusted to run against the genuine data.

#### 10. All checks were run against the complete tables

The full register was run once, top to bottom, against the final six tables and displayed as a single result table.

### Important decisions

A failing check is not automatically turned into a raised exception; the register is displayed in full first, and any failure is read and interpreted before deciding whether to correct the code or document a genuine finding, consistent with the specification's instruction that a reported failure is not automatically incorrect.

Date and timestamp fields are parsed only transiently, inside each temporal check, on a copy of the relevant column; the underlying table's required export string format is never modified.

Categorical-field checks use a cardinality threshold (a small, bounded number of distinct values) rather than a hard-coded expected list, so a check remains meaningful without assuming the exact certified categories.

## How the work is run

`Group018_solution.ipynb` is opened, the kernel is restarted, and all cells are run from top to bottom, including the completed Task 1 and Task 2 sections. The Task 3 public and student-designed text-function checks, the eleven deferred-field derivations, the Task 4 validation register, and the final six-CSV export are expected to complete without network access or manual edits.

