# Task 1 - Source Profiling and Mapping

## Purpose

Task 1 was completed by treating the assignment specification and marking rubric as the ultimate sources of truth. The public data dictionary, Group018 README, manifest, and official teaching templates were used as supporting contracts.

The code was kept explicit so that each decision can be understood by a beginner. JSON parsing, XML parsing, profiling, reconciliation, and mapping were not combined into one hidden pipeline. Short inline comments were added for each logical block, and simple docstrings were added for every function.

## Files used

The following Group018 sources were used:

- `data/raw_input/Group018_commerce.json`
- `data/raw_input/Group018_operations.xml`
- `data/A1_manifest.json`
- `data/public_data_dictionary.csv`
- `data/README.md`

The official solution-notebook and source-to-target mapping templates from `templates/` were used.

## Steps taken and reasons

### 1. Reproducible paths were configured

`GROUP_ID`, `INPUT_DIR`, `OUTPUT_DIR`, and `TEMPLATE_DIR` were placed in one notebook section. This was done because the final notebook must run on another computer without student-specific absolute paths.

### 2. The package was verified

The Group018 alias, required filenames, file sizes, and SHA-256 hashes were checked against the manifest. This was done because every later result would be invalidated if the wrong or modified source package were profiled. The notebook evidence is in Section 0.2, "Package identity and integrity."

### 3. JSON was parsed structurally

`json.load` was used, and the top-level metadata, order headers, product catalogue, and product reviews were inspected. This was done because reconstructing JSON structure with regular expressions is prohibited by the specification. The notebook evidence is in Sections 1.1 to 1.1.2.

### 4. XML was parsed structurally

`xml.etree.ElementTree` was used, and customers, orders, shopping-cart items, deliveries, product reviews, and the warehouse directory were inspected. It was observed that cart items repeat inside orders. Therefore, order items are treated as a separate grain instead of an order being forced into one flat row. The notebook evidence is in Sections 1.2 to 1.2.2.

### 5. Formats and missing values were profiled

Native JSON numbers and booleans with ISO-style timestamps were observed. XML strings containing day-first dates, `Y`/`N` booleans, `AUD` currency labels, thousands separators, and percent signs were also observed. Therefore, source-specific conversion rules were recorded before fields were compared. The notebook evidence is in Section 1.3.

### 6. Keys and relationships were investigated

Missing and duplicate values were measured for every candidate primary key. The required foreign-key relationships were also checked by using the broader source for overlapping entities. This was done because completeness, uniqueness, or referential integrity are not proved by names such as `Order_ID`. The notebook evidence is in Sections 1.4 and 1.5.

### 7. Duplication and overlap were investigated

Candidate-key duplication was checked within every source collection. Order and review keys were then compared across JSON and XML. Cross-source overlap was observed, so those collections will not be concatenated. They will be reconciled by stable key after normalisation. The notebook evidence is in Sections 1.6 and 1.7.

### 8. Overlapping fields were compared

Only the formats needed for profiling were normalised, and overlapping order and review fields were compared. Text, timestamp, money, percentage, boolean, and numeric comparison rules were kept separate. This was done so that the comparison can be audited and JSON or XML is not silently preferred. The notebook evidence is in Sections 1.8 and 1.9.

### 9. Assumptions were recorded

The observed source for every target table, its intended grain, and its candidate key were recorded. It was also recorded that any different non-missing values for the same normalised field and key must be reported as conflicts. This was done because arbitrary source precedence is prohibited by the specification. The notebook evidence is in Section 1.10.

### 10. The mapping was completed and checked

Every row of the official 111-row source-to-target mapping was completed. The official headers, mapping IDs, target fields, and row order were preserved. The result was then checked against the official template and public data dictionary. The notebook evidence is in Sections 2.1 and 2.2.

## Important decisions

XML is used as the broader order source and JSON is used as the broader review source only for coverage checks. This fact is not used as an automatic value-precedence rule.

Identifiers, leading zeros, structured category case, and valid Unicode content are preserved. Entity identities are not invented.

A source-level empty value is distinguished from the literal output string `NaN`. The prescribed `NaN` sentinel will be applied only during the relevant later transformations.

Future arithmetic and text derivations have been described in the mapping because complete lineage for every target field is required by Task 1. The six standardised output tables have not been created in this milestone.

## How the work is run

`Group018_solution.ipynb` is opened, the kernel is restarted, and all cells are run from top to bottom. The package checks, profiling tables, overlap comparisons, and mapping validation are expected to complete without network access or manual edits.

## Current limitation

Group-member names and student IDs have been left as a visible placeholder because they were not supplied. All unfinished later-task template sections were removed so that the notebook contains Task 1 only.
