# Task 3 Handoff

## Use the completed work

Read the completed Task 1 profiling and source-to-target mapping before changing the pipeline.

Treat the structured JSON/XML parsing, source profiling, key investigation and mapping as completed.

Reuse the Task 2 normalisation, staging, reconciliation and arithmetic results.

Reuse `orders_stage["customer_note_raw"]`, `deliveries_stage["delivery_note_raw"]`, `products_stage["product_description_raw"]` and `product_reviews_stage["review_text_raw"]`.

Do not reconstruct JSON or XML structure with regular expressions.

Preserve every completed Task 2 field and all six relational grains.

Note that the current interim CSVs contain 100 of the required 111 fields.

## Implement the required functions

Create `Group018_text_functions.py`.

Implement `clean_narrative_text(value)`.

Implement `extract_order_reference(value)`.

Implement `extract_product_sku(value)`.

Implement `extract_promo_code(value)`.

Implement `build_latin_analysis(value)`.

Implement `contains_non_latin_script(value)`.

Add a simple docstring to every function.

Add short inline comments before each important logical step.

Keep every function free from file input/output, network calls and row-specific lookups.

## Follow the published text rules

Extract required order, SKU and promotion references from raw text before cleaning it.

Decode HTML entities and apply Unicode NFC normalisation.

Remove HTML/XML-like tags while retaining readable content.

Remove every published system, source, rating and social marker.

Remove URLs and emoji.

Remove complete review-reference wrappers and promotion wrappers.

Collapse repeated whitespace, trim the result and lower-case the designated cleaned narrative.

Return the literal string `NaN` when no readable text remains.

Preserve valid multilingual UTF-8 letters in `review_body_clean`.

Build `review_body_latin_analysis` from `review_body_clean`, not from raw review text.

Preserve Latin-script letters and European diacritics in the Latin analysis.

Remove non-Latin letters from the Latin analysis.

Detect non-Latin letters by Unicode script rather than by non-ASCII status.

Reject malformed, embedded and overlong near-match references.

Return valid extracted references in upper case.

## Add the deferred target fields

Import the six fixed functions into `Group018_solution.ipynb`.

Create `orders.customer_note_clean` from `orders_stage["customer_note_raw"]`.

Create `orders.promo_code` from `orders_stage["customer_note_raw"]`.

Create `deliveries.delivery_note_clean` from `deliveries_stage["delivery_note_raw"]`.

Create `products.product_description_clean` from `products_stage["product_description_raw"]`.

Create `product_reviews.review_body_clean` from `product_reviews_stage["review_text_raw"]`.

Create `product_reviews.review_body_latin_analysis` from `review_body_clean`.

Create `product_reviews.review_length_chars` from the number of Python characters in `review_body_clean`.

Create `product_reviews.review_word_count` from the number of whitespace-separated tokens in `review_body_clean`.

Create `product_reviews.contains_non_latin_script` as a Python boolean.

Create `product_reviews.extracted_order_reference` from raw review text.

Create `product_reviews.extracted_product_sku` from raw review text.

Insert all 11 fields into their exact public-dictionary positions.

## Verify Task 3

Load `templates/A1_public_text_test_cases.csv` with `keep_default_na=False`.

Run every supplied public case.

Add focused student-designed cases inside the notebook.

Cover matched, unmatched, missing, multilingual and near-match inputs.

Check every fixed function name, argument count and return contract.

Check literal `NaN` behaviour separately from Python and pandas missing values.

Check multilingual preservation and Latin-analysis separation.

Check order, SKU and promotion reference extraction.

Do not create a separate test file unless the specification explicitly requires it.

## Finalise the submission outputs

Replace the red interim warning with a completed Task 3 observation.

Overwrite the six interim CSVs with complete versions.

Confirm that all 111 fields exist in the required order.

Re-run all schema, type, key, relationship, source-flow, arithmetic, temporal and text checks.

Restart the notebook kernel and run every cell from top to bottom.

Regenerate `Group018_solution.py` from the completed notebook.

Keep all work on `master` and create no commit unless a later instruction explicitly requests one.
