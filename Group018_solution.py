#!/usr/bin/env python
# coding: utf-8

# # FIT5196 Assessment 1 -
# 
# **Group:** Group018  
# **Members:** 

# ## 0. Configuration and reproducibility
# 
# All paths are kept in one place so that the notebook can be run on another computer without editing code throughout the notebook. Relative paths are used, and no network service is used.
# 

# In[1]:


from pathlib import Path

# Group name and folders
GROUP_ID = "Group018"
INPUT_DIR = Path("data/raw_input")
OUTPUT_DIR = Path("outputs")
TEMPLATE_DIR = Path("templates")
DATA_DIR = Path("data")

# Output folder
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Analysing {GROUP_ID}.")
print(f"Reading raw files from: {INPUT_DIR}")
print(f"Using templates from: {TEMPLATE_DIR}")


# ### 0.1 Environment and dependencies

# In[2]:


# Standard-library imports for files, hashing, dates, counters and XML parsing.
import hashlib
import json
import platform
from collections import Counter
from datetime import datetime
import xml.etree.ElementTree as ET


import pandas as pd

try:
    from IPython.display import display
except ImportError:
    def display(value):
        """Print a readable fallback when IPython display is unavailable."""
        if isinstance(value, pd.DataFrame):
            print(value.to_string(index=False))
        else:
            print(value)

print(f"Python version: {platform.python_version()}")
print(f"pandas version: {pd.__version__}")


# ### 0.2 Package identity and integrity
# 
# The manifest is inspected before the data is read. This is done because the assessment is group-specific, and every later result would be invalidated if another group's files were used.
# 

# In[3]:


# Define every supplied file from the configuration above.
MANIFEST_PATH = DATA_DIR / "A1_manifest.json"
README_PATH = DATA_DIR / "README.md"
DICTIONARY_PATH = DATA_DIR / "public_data_dictionary.csv"
JSON_PATH = INPUT_DIR / f"{GROUP_ID}_commerce.json"
XML_PATH = INPUT_DIR / f"{GROUP_ID}_operations.xml"

required_paths = [
    MANIFEST_PATH,
    README_PATH,
    DICTIONARY_PATH,
    JSON_PATH,
    XML_PATH,
]

# Stop early if a required input is missing.
for path in required_paths:
    if not path.exists():
        raise FileNotFoundError(f"Required file is missing: {path}")

# Parse the manifest as structured JSON.
with MANIFEST_PATH.open("r", encoding="utf-8") as file:
    manifest = json.load(file)

print("Manifest group alias:", manifest["group_alias"])
print("Manifest schema version:", manifest["manifest_schema_version"])

# The configured group must agree with the package metadata.
if manifest["group_alias"] != GROUP_ID:
    raise ValueError("The configured group does not match the manifest group alias.")

def calculate_sha256(file_path):
    """Calculate and return the SHA-256 hash of one file."""
    file_bytes = file_path.read_bytes()
    return hashlib.sha256(file_bytes).hexdigest()

# Compare each supplied file with its size and hash in the manifest.
integrity_rows = []

for manifest_file in manifest["files"]:
    file_path = DATA_DIR / manifest_file["path"]
    actual_bytes = file_path.stat().st_size
    actual_sha256 = calculate_sha256(file_path)

    integrity_rows.append(
        {
            "file": manifest_file["path"],
            "size_matches": actual_bytes == manifest_file["bytes"],
            "sha256_matches": actual_sha256 == manifest_file["sha256"],
        }
    )

integrity_checks = pd.DataFrame(integrity_rows)
display(integrity_checks)

passed_files = integrity_checks[["size_matches", "sha256_matches"]].all(axis=1).sum()
print(f"Files passing size and SHA-256 checks: {passed_files} of {len(integrity_checks)}")

if passed_files != len(integrity_checks):
    raise ValueError("At least one supplied file does not match the manifest.")


# **Observation and decision:** Four files were listed in the manifest. All four files matched their recorded byte sizes and SHA-256 hashes. Therefore, the supplied files were treated as unchanged.
# 

# ## 1. Parse and profile the two sources
# 
# Structure, grain, keys, formats, missing values, and overlap are inspected first. This is done before transformation so that evidence is available for the mapping and source problems are not hidden by cleaning decisions.
# 

# ### 1.1 JSON structure and profile
# 
# The commerce file is parsed with `json.load` because a structured JSON parser is required by the specification.
# 

# In[4]:


# Parse the complete commerce export as JSON.
with JSON_PATH.open("r", encoding="utf-8") as file:
    commerce_data = json.load(file)

# Print the root structure and source metadata before inspecting records.
print("JSON root type:", type(commerce_data).__name__)
print("JSON top-level keys:", list(commerce_data.keys()))
display(pd.DataFrame([commerce_data["exportMetadata"]]))


# **Observation and decision:** The JSON root is a dictionary with four top-level keys: `exportMetadata`, `orderHeaders`, `productCatalog`, and `productReviews`. The source is identified by the metadata as `CommercePlatform` for Group018 and period 2018. Therefore, the three repeated lists are treated as separate source collections rather than one flat table.
# 

# In[5]:


# Count each repeated JSON collection without assuming an expected total.
json_collection_rows = []

for collection_name in ["orderHeaders", "productCatalog", "productReviews"]:
    records = commerce_data[collection_name]
    first_record = records[0]

    json_collection_rows.append(
        {
            "collection": collection_name,
            "data_type": type(records).__name__,
            "record_count": len(records),
            "first_record_type": type(first_record).__name__,
            "field_count": len(first_record),
        }
    )

json_collections = pd.DataFrame(json_collection_rows)

for row in json_collections.itertuples(index=False):
    print(f"{row.collection}: {row.record_count:,} records and {row.field_count} fields in the first record")

display(json_collections)


# **Observation and decision:** The calculated counts show 1,100 order headers, 1,000 products, and 7,000 reviews. It was observed that `orderHeaders` contains one raw JSON order header per list element, `productCatalog` contains one raw product per element, and `productReviews` contains one raw review per element. Therefore, each collection is profiled at its own grain.
# 

# #### 1.1.1 JSON nesting and example fields
# 
# Field names and small examples are inspected instead of complete records being printed. This is done because review text is long and the structure can be audited more easily in a compact view.
# 

# In[6]:


# Keep clear names for the three JSON record collections.
json_orders = commerce_data["orderHeaders"]
json_products = commerce_data["productCatalog"]
json_reviews = commerce_data["productReviews"]

# Only the structural fields are printed; the grain is explained in markdown below.
json_structure = pd.DataFrame(
    [
        {"collection": "orderHeaders", "fields": " | ".join(json_orders[0].keys())},
        {"collection": "productCatalog", "fields": " | ".join(json_products[0].keys())},
        {"collection": "productReviews", "fields": " | ".join(json_reviews[0].keys())},
    ]
)
display(json_structure)

# Show an example of IDs, dates and booleans from each collection.
json_examples = pd.DataFrame(
    [
        {
            "collection": "orderHeaders",
            "id": json_orders[0]["orderID"],
            "date_or_timestamp": json_orders[0]["orderTimestamp"],
            "boolean_example": json_orders[0]["expeditedDelivery"],
        },
        {
            "collection": "productCatalog",
            "id": json_products[0]["productID"],
            "date_or_timestamp": json_products[0]["launchDate"],
            "boolean_example": json_products[0]["activeFlag"],
        },
        {
            "collection": "productReviews",
            "id": json_reviews[0]["reviewID"],
            "date_or_timestamp": json_reviews[0]["reviewTimestamp"],
            "boolean_example": json_reviews[0]["verifiedPurchase"],
        },
    ]
)
display(json_examples)


# **Observation and decision:** It was observed that `orderID`, `productID`, and `reviewID` are present in their respective example records and are possible candidate keys.
# 

# #### 1.1.2 JSON field profile
# 
# Missing values, Python types, and unique values are counted for every field. Both `None` and an empty string are treated as source-level missing representations. They are kept separate from the required literal `NaN` output rule, which belongs to later transformation work.
# 

# In[7]:


def profile_dictionary_records(records):
    """Create a simple field profile for a list of dictionary records.

    Parameters
    ----------
    records : list of dict
        Records from one JSON or XML collection.

    Returns
    -------
    pandas.DataFrame
        One row per field with missing counts, types, uniqueness and an example.
    """
    # Find every field that appears anywhere in the collection.
    field_names = sorted({field for record in records for field in record.keys()})
    profile_rows = []

    for field_name in field_names:
        # Read the same field from every record.
        values = [record.get(field_name) for record in records]

        # Treat None and an empty string as missing only
        missing_count = sum(value is None or value == "" for value in values)
        non_missing_values = [value for value in values if value is not None and value != ""]

        # Record the observed types and a short example without changing the data
        type_names = sorted({type(value).__name__ for value in non_missing_values})
        example_value = non_missing_values[0] if non_missing_values else None

        profile_rows.append(
            {
                "field": field_name,
                "row_count": len(values),
                "missing_count": missing_count,
                "missing_percent": round(100 * missing_count / len(values), 2),
                "python_types": " | ".join(type_names),
                "unique_non_missing": len(set(map(str, non_missing_values))),
                "example": str(example_value)[:100],
            }
        )

    return pd.DataFrame(profile_rows)


# In[8]:


# Profile each JSON collection separately so its grain remains clear.
json_order_profile = profile_dictionary_records(json_orders)
json_product_profile = profile_dictionary_records(json_products)
json_review_profile = profile_dictionary_records(json_reviews)

# Print the calculated missing-value totals used in the following observation.
print("Empty JSON order couponCode values:", int(json_order_profile.loc[json_order_profile["field"] == "couponCode", "missing_count"].iloc[0]))
print("Total empty values across JSON product fields:", int(json_product_profile["missing_count"].sum()))
print("Total empty values across JSON review fields:", int(json_review_profile["missing_count"].sum()))

print("JSON order-header profile")
display(json_order_profile)

print("JSON product profile")
display(json_product_profile)

print("JSON review profile")
display(json_review_profile)


# **Observation and decision:** The field profiles show that JSON order headers have 688 empty `couponCode` values, while the profiled product and review fields have no empty or `None` values. Native JSON numeric and boolean types were also observed. Therefore, empty coupon values are kept visible during profiling, and the prescribed output `NaN` treatment is deferred to transformation.
# 

# ### 1.2 XML structure and profile
# 
# The operations file is parsed with `ElementTree.parse`. Repeated elements are inspected without using regular expressions to rebuild the XML hierarchy.
# 

# In[9]:


# Parse the XML document and keep its root element.
xml_tree = ET.parse(XML_PATH)
xml_root = xml_tree.getroot()

print("XML root tag:", xml_root.tag)
print("XML root attributes:", xml_root.attrib)
print("XML root child tags:", [child.tag for child in xml_root])


# **Observation and decision:** The root tag `OperationsExport` with Group018, `OperationsERP`, and period 2018 attributes. Its major child sections are metadata, customers, orders, product reviews, and the warehouse directory. 
# 

# In[10]:


# Select the major repeated XML entity elements using structural paths.
xml_customer_elements = xml_root.findall("./Customers/Customer")
xml_order_elements = xml_root.findall("./Orders/Order")
xml_review_elements = xml_root.findall("./ProductReviews/Review")
xml_warehouse_elements = xml_root.findall("./WarehouseDirectory/Warehouse")

# Separate the nested order header, cart-item and delivery elements.
xml_header_elements = []
xml_item_elements = []
xml_delivery_elements = []

for order_element in xml_order_elements:
    header_element = order_element.find("./Header")
    if header_element is not None:
        xml_header_elements.append(header_element)

    for item_element in order_element.findall("./Shopping_Cart/Item"):
        xml_item_elements.append(item_element)

    for delivery_element in order_element.findall("./Delivery"):
        xml_delivery_elements.append(delivery_element)

# Print calculated collection counts; grain decisions are explained in markdown.
xml_collection_summary = pd.DataFrame(
    [
        {"collection": "Customers/Customer", "record_count": len(xml_customer_elements)},
        {"collection": "Orders/Order/Header", "record_count": len(xml_header_elements)},
        {"collection": "Orders/Order/Shopping_Cart/Item", "record_count": len(xml_item_elements)},
        {"collection": "Orders/Order/Delivery", "record_count": len(xml_delivery_elements)},
        {"collection": "ProductReviews/Review", "record_count": len(xml_review_elements)},
        {"collection": "WarehouseDirectory/Warehouse", "record_count": len(xml_warehouse_elements)},
    ]
)

for row in xml_collection_summary.itertuples(index=False):
    print(f"{row.collection}: {row.record_count:,} records")

display(xml_collection_summary)


# **Observation and decision:** The calculated XML counts show 500 customers, 5,000 order headers, 15,618 order items, 5,000 deliveries, 1,260 reviews, and 3 warehouse records. It was observed that there is one raw XML customer per `Customer`, one raw order header per `Header`, one item per repeated `Item`, one delivery per `Delivery`, and one review per `Review`. Therefore, these are kept as separate source grains.
# 

# #### 1.2.1 XML nesting and repeated elements
# 
# The children of one XML order are inspected, and the numbers of item and delivery elements in each order are calculated. The grain decision is explained after the calculated output.
# 

# In[11]:


# Inspect the structure of one order without changing it.
first_xml_order = xml_order_elements[0]

print("Children inside one XML Order:", [child.tag for child in first_xml_order])
print("Fields inside its Header:", [child.tag for child in first_xml_order.find("./Header")])
print("Fields inside its first Item:", [child.tag for child in first_xml_order.find("./Shopping_Cart/Item")])
print("Fields inside its Delivery:", [child.tag for child in first_xml_order.find("./Delivery")])

# Count repeated items and deliveries separately for every order.
item_counts_per_order = []
delivery_counts_per_order = []

for order_element in xml_order_elements:
    item_counts_per_order.append(len(order_element.findall("./Shopping_Cart/Item")))
    delivery_counts_per_order.append(len(order_element.findall("./Delivery")))

xml_repetition_summary = pd.DataFrame(
    [
        {
            "repeated_element": "Shopping_Cart/Item",
            "minimum_per_order": min(item_counts_per_order),
            "maximum_per_order": max(item_counts_per_order),
        },
        {
            "repeated_element": "Delivery",
            "minimum_per_order": min(delivery_counts_per_order),
            "maximum_per_order": max(delivery_counts_per_order),
        },
    ]
)

print(f"Items per order range: {min(item_counts_per_order)} to {max(item_counts_per_order)}")
print(f"Deliveries per order range: {min(delivery_counts_per_order)} to {max(delivery_counts_per_order)}")
display(xml_repetition_summary)


# **Observation and decision:** The calculated range shows between 1 and 5 cart items per order and exactly 1 delivery per order in this source. It was also observed that each order contains separate `Header`, `Shopping_Cart`, and `Delivery` children. Therefore, an order is not flattened into one wide row, and the one-to-many item relationship is retained.
# 

# #### 1.2.2 Convert XML elements into profiling dictionaries
# 
# Only direct child elements are converted into small dictionaries after structured parsing. This keeps field profiling readable while preserving the parent-child paths found in the XML.
# 

# In[12]:


def direct_children_to_dictionary(element):
    """Convert one XML element's direct children into a simple dictionary.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        One already-parsed XML entity element.

    Returns
    -------
    dict
        Child tag names mapped to their text values.
    """
    record = {}

    # Read direct children only so nested entity grains are not mixed together.
    for child in element:
        record[child.tag] = child.text if child.text is not None else ""

    return record


# Convert each XML entity collection separately.
xml_customers = [direct_children_to_dictionary(element) for element in xml_customer_elements]
xml_headers = [direct_children_to_dictionary(element) for element in xml_header_elements]
xml_items = [direct_children_to_dictionary(element) for element in xml_item_elements]
xml_deliveries = [direct_children_to_dictionary(element) for element in xml_delivery_elements]
xml_reviews = [direct_children_to_dictionary(element) for element in xml_review_elements]
xml_warehouses = [direct_children_to_dictionary(element) for element in xml_warehouse_elements]


# In[13]:


# Profile each XML entity collection at its own grain.
xml_customer_profile = profile_dictionary_records(xml_customers)
xml_header_profile = profile_dictionary_records(xml_headers)
xml_item_profile = profile_dictionary_records(xml_items)
xml_delivery_profile = profile_dictionary_records(xml_deliveries)
xml_review_profile = profile_dictionary_records(xml_reviews)

# Print the calculated missing-value totals used in the following observation.
print("Empty XML order Coupon_Code values:", int(xml_header_profile.loc[xml_header_profile["field"] == "Coupon_Code", "missing_count"].iloc[0]))
print("Total empty values across XML customer fields:", int(xml_customer_profile["missing_count"].sum()))
print("Total empty values across XML item fields:", int(xml_item_profile["missing_count"].sum()))
print("Total empty values across XML delivery fields:", int(xml_delivery_profile["missing_count"].sum()))
print("Total empty values across XML review fields:", int(xml_review_profile["missing_count"].sum()))

print("XML customer profile")
display(xml_customer_profile)

print("XML order-header profile")
display(xml_header_profile)

print("XML order-item profile")
display(xml_item_profile)

print("XML delivery profile")
display(xml_delivery_profile)

print("XML review profile")
display(xml_review_profile)


# **Observation and decision:** The XML field profiles show 3,155 empty `Coupon_Code` values in the order headers. The profiled customer, item, delivery, and review fields have no empty text values. 

# ### 1.3 Source formats and missing-value conventions
# 
# Representative raw values are printed before normalisation. The following markdown observation is used to explain what these calculated examples mean for later transformations.
# 

# In[14]:


# Place equivalent JSON and XML values side by side.
format_examples = pd.DataFrame(
    [
        {"concept": "timestamp", "JSON_example": json_orders[0]["orderTimestamp"], "XML_example": xml_headers[0]["Order_Timestamp"]},
        {"concept": "boolean", "JSON_example": json_orders[0]["expeditedDelivery"], "XML_example": xml_headers[0]["Expedited_Delivery"]},
        {"concept": "currency", "JSON_example": json_orders[0]["orderPrice"], "XML_example": xml_headers[0]["Order_Price"]},
        {"concept": "percentage points", "JSON_example": json_orders[0]["couponDiscount"], "XML_example": xml_headers[0]["Coupon_Discount"]},
        {"concept": "coupon missing representation", "JSON_example": repr(json_orders[0]["couponCode"]), "XML_example": repr(xml_headers[0]["Coupon_Code"])},
    ]
)

display(format_examples)


# **Observation and decision:** ISO-style JSON timestamps and day-first XML timestamps, native JSON booleans and XML `Y`/`N`, numeric JSON money and XML `AUD` strings with separators, and numeric JSON discounts versus XML percent strings were observed. Therefore, separate and explicit normalisation rules are used before cross-source comparison.
# 

# ### 1.4 Candidate primary keys
# 
# Completeness and uniqueness are calculated for each candidate key. 
# 

# In[15]:


def check_candidate_key(source_name, records, key_field):
    """Measure whether a candidate key is complete and unique.

    Parameters
    ----------
    source_name : str
        Readable collection name used in the result.
    records : list of dict
        Records from one source collection.
    key_field : str
        Field being tested as the collection's candidate key.

    Returns
    -------
    dict
        Counts for rows, missing keys, unique keys and duplicate keys.
    """
    # Collect all key values without changing their case or leading zeros.
    key_values = [record.get(key_field) for record in records]
    missing_count = sum(value is None or value == "" for value in key_values)
    key_counts = Counter(key_values)

    # Count duplicate key groups
    duplicate_keys = [
        key
        for key, count in key_counts.items()
        if key not in {None, ""} and count > 1
    ]

    return {
        "source_collection": source_name,
        "candidate_key": key_field,
        "row_count": len(records),
        "missing_key_count": missing_count,
        "unique_non_missing_keys": len({value for value in key_values if value not in {None, ""}}),
        "duplicate_key_count": len(duplicate_keys),
        "maximum_key_frequency": max(key_counts.values()) if key_counts else 0,
    }


# Run the same key test separately for every source entity collection.
candidate_key_checks = pd.DataFrame(
    [
        check_candidate_key("JSON orderHeaders", json_orders, "orderID"),
        check_candidate_key("JSON productCatalog", json_products, "productID"),
        check_candidate_key("JSON productReviews", json_reviews, "reviewID"),
        check_candidate_key("XML Customers/Customer", xml_customers, "Customer_ID"),
        check_candidate_key("XML Orders/Order/Header", xml_headers, "Order_ID"),
        check_candidate_key("XML Shopping_Cart/Item", xml_items, "Order_Item_ID"),
        check_candidate_key("XML Delivery", xml_deliveries, "Delivery_ID"),
        check_candidate_key("XML ProductReviews/Review", xml_reviews, "Review_ID"),
    ]
)

display(candidate_key_checks)
print("Total missing candidate keys:", int(candidate_key_checks["missing_key_count"].sum()))
print("Total duplicate candidate-key groups:", int(candidate_key_checks["duplicate_key_count"].sum()))


# **Observation and decision:** The calculated key checks show zero missing values and zero duplicate groups for all eight candidate source keys. Their unique non-missing counts equal their row counts. Therefore, they are accepted as candidate primary keys for mapping and relationship checks, while retaining executable duplicate checks for reproducibility.
# 

# ### 1.5 Candidate foreign-key relationships
# 
# The existence of child identifiers in their expected parent collections is checked. The broader source is used for overlapping entities so that false orphan results are not created by source-coverage differences.
# 

# In[16]:


# Create parent-key sets once so each relationship check is easy to read.
xml_order_ids = {record["Order_ID"] for record in xml_headers}
xml_customer_ids = {record["Customer_ID"] for record in xml_customers}
xml_item_ids = {record["Order_Item_ID"] for record in xml_items}
json_product_ids = {record["productID"] for record in json_products}


def check_foreign_key(relationship, child_values, parent_values):
    """Count missing and orphan values for one candidate relationship.

    Parameters
    ----------
    relationship : str
        Readable child-to-parent relationship name.
    child_values : list
        Foreign-key values from the child records.
    parent_values : set
        Valid primary-key values from the parent records.

    Returns
    -------
    dict
        Child-row count plus missing and orphan-key counts.
    """
    missing_values = [value for value in child_values if value is None or value == ""]
    orphan_values = sorted(
        {
            value
            for value in child_values
            if value not in {None, ""} and value not in parent_values
        }
    )

    return {
        "relationship": relationship,
        "child_rows": len(child_values),
        "missing_child_keys": len(missing_values),
        "distinct_orphan_keys": len(orphan_values),
        "orphan_example": orphan_values[0] if orphan_values else "",
    }


# Test each required relationship separately.
foreign_key_checks = pd.DataFrame(
    [
        check_foreign_key("orders.customer_id -> customers.customer_id", [record["Customer_ID"] for record in xml_headers], xml_customer_ids),
        check_foreign_key("order_items.order_id -> orders.order_id", [record["Order_ID"] for record in xml_items], xml_order_ids),
        check_foreign_key("order_items.product_id -> products.product_id", [record["Product_ID"] for record in xml_items], json_product_ids),
        check_foreign_key("deliveries.order_id -> orders.order_id", [record["Order_ID"] for record in xml_deliveries], xml_order_ids),
        check_foreign_key("reviews.order_id -> orders.order_id", [record["orderID"] for record in json_reviews], xml_order_ids),
        check_foreign_key("reviews.order_item_id -> order_items.order_item_id", [record["orderItemID"] for record in json_reviews], xml_item_ids),
        check_foreign_key("reviews.product_id -> products.product_id", [record["productID"] for record in json_reviews], json_product_ids),
        check_foreign_key("reviews.customer_id -> customers.customer_id", [record["customerID"] for record in json_reviews], xml_customer_ids),
    ]
)

display(foreign_key_checks)
print("Total missing child keys:", int(foreign_key_checks["missing_child_keys"].sum()))
print("Total distinct orphan keys across checks:", int(foreign_key_checks["distinct_orphan_keys"].sum()))


# **Observation and decision:** The calculated relationship checks show zero missing child keys and zero orphan keys for all eight required relationships. Therefore, the source records support the proposed relational links at the observed grains.
# 

# ### 1.6 Within-source duplicates
# 
# The candidate-key results are reused to report duplicate key groups within each source collection. These values are calculated rather than obtained from a hard-coded identifier list.
# 

# In[17]:


# Keep only the columns needed to understand within-source duplication.
within_source_duplicates = candidate_key_checks[
    ["source_collection", "candidate_key", "row_count", "duplicate_key_count", "maximum_key_frequency"]
].copy()

display(within_source_duplicates)

# Print the calculated total; the interpretation is in markdown below.
total_duplicate_key_groups = int(within_source_duplicates["duplicate_key_count"].sum())
print("Total duplicate candidate-key groups:", total_duplicate_key_groups)


# **Observation and decision:** There are zero duplicate candidate-key groups within the profiled source collections. Therefore, no rows are removed during Task 1, but data-driven duplicate checks are retained for the later canonicalisation workflow.
# 

# ### 1.7 Cross-source overlap
# 
# Stable order and review identifier overlap across JSON and XML is calculated. This is done because overlapping records would be counted twice if they were appended.
# 

# In[18]:


# Build unique key sets for the two entities present in both sources.
json_order_ids = {record["orderID"] for record in json_orders}
xml_order_ids = {record["Order_ID"] for record in xml_headers}
json_review_ids = {record["reviewID"] for record in json_reviews}
xml_review_ids = {record["Review_ID"] for record in xml_reviews}

# Calculate intersections and source-only coverage.
overlap_summary = pd.DataFrame(
    [
        {
            "entity": "orders",
            "JSON_unique_keys": len(json_order_ids),
            "XML_unique_keys": len(xml_order_ids),
            "intersection": len(json_order_ids & xml_order_ids),
            "JSON_only": len(json_order_ids - xml_order_ids),
            "XML_only": len(xml_order_ids - json_order_ids),
        },
        {
            "entity": "product_reviews",
            "JSON_unique_keys": len(json_review_ids),
            "XML_unique_keys": len(xml_review_ids),
            "intersection": len(json_review_ids & xml_review_ids),
            "JSON_only": len(json_review_ids - xml_review_ids),
            "XML_only": len(xml_review_ids - json_review_ids),
        },
    ]
)

display(overlap_summary)

for row in overlap_summary.itertuples(index=False):
    print(
        f"{row.entity}: {row.intersection:,} overlapping, "
        f"{row.JSON_only:,} JSON-only, {row.XML_only:,} XML-only keys"
    )


# **Observation and decision:** 1,100 overlapping order keys were observed, with 3,900 XML-only orders and no JSON-only orders. 1,260 overlapping review keys were also observed, with 5,740 JSON-only reviews and no XML-only reviews. Therefore, orders and reviews will be reconciled by stable key instead of the sources being concatenated or automatic source precedence being applied.
# 

# ### 1.8 Normalised comparison of overlapping orders
# 
# Only the comparable formats needed for profiling are normalised. Each rule is kept in a separate function so that its purpose is visible and testable.
# 

# In[19]:


def normalise_text_for_comparison(value):
    """Trim a value for comparison and represent None as an empty string."""
    if value is None:
        return ""
    return str(value).strip()


def normalise_timestamp_for_comparison(value, source_format):
    """Convert a JSON or XML timestamp to the common target timestamp format."""
    if source_format == "JSON":
        parsed_value = datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M:%S")
    else:
        parsed_value = datetime.strptime(str(value).strip(), "%d/%m/%Y %H:%M:%S")
    return parsed_value.strftime("%Y-%m-%d %H:%M:%S")


def normalise_money_for_comparison(value):
    """Remove the XML currency label and separator, then return two decimals."""
    text_value = str(value).replace("AUD", "").replace(",", "").strip()
    return round(float(text_value), 2)


def normalise_percentage_for_comparison(value):
    """Return numeric percentage points after removing an optional percent sign."""
    text_value = str(value).replace("%", "").strip()
    return float(text_value)


def normalise_boolean_for_comparison(value):
    """Keep a native boolean or convert an XML Y/N value to True/False."""
    if isinstance(value, bool):
        return value
    text_value = str(value).strip().upper()
    return {"Y": True, "N": False}[text_value]


def normalise_number_for_comparison(value):
    """Convert a numeric source value to float for a like-for-like comparison."""
    return float(str(value).strip())


# In[20]:


# Index both order sources by their stable order ID.
json_orders_by_id = {record["orderID"]: record for record in json_orders}
xml_orders_by_id = {record["Order_ID"]: record for record in xml_headers}

# List each comparable target field and its source-specific field names.
order_comparison_rules = [
    ("source_system_record_id", "sourceSystemRecordID", "Source_System_Record_ID", normalise_text_for_comparison),
    ("customer_id", "customerID", "Customer_ID", normalise_text_for_comparison),
    ("sales_channel", "salesChannel", "Sales_Channel", normalise_text_for_comparison),
    ("payment_method", "paymentMethod", "Payment_Method", normalise_text_for_comparison),
    ("currency", "currency", "Currency", normalise_text_for_comparison),
    ("nearest_warehouse", "nearestWarehouse", "Nearest_Warehouse", normalise_text_for_comparison),
    ("order_status", "orderStatus", "Order_Status", normalise_text_for_comparison),
    ("order_price_supplied", "orderPrice", "Order_Price", normalise_money_for_comparison),
    ("delivery_charges", "deliveryCharges", "Delivery_Charges", normalise_money_for_comparison),
    ("coupon_code", "couponCode", "Coupon_Code", normalise_text_for_comparison),
    ("coupon_discount", "couponDiscount", "Coupon_Discount", normalise_percentage_for_comparison),
    ("tax_amount_supplied", "taxAmount", "Tax_Amount", normalise_money_for_comparison),
    ("order_total_supplied", "orderTotal", "Order_Total", normalise_money_for_comparison),
    ("season", "season", "Season", normalise_text_for_comparison),
    ("expedited_delivery", "expeditedDelivery", "Expedited_Delivery", normalise_boolean_for_comparison),
    ("customer_lat", "customerLat", "Customer_Lat", normalise_number_for_comparison),
    ("customer_long", "customerLong", "Customer_Long", normalise_number_for_comparison),
    ("device_type", "deviceType", "Device_Type", normalise_text_for_comparison),
    ("referral_source", "referralSource", "Referral_Source", normalise_text_for_comparison),
    ("customer_note_raw", "customerNote", "Customer_Note", normalise_text_for_comparison),
]

# Compare every overlapping order one field at a time.
order_comparison_rows = []

for target_field, json_field, xml_field, normalise_function in order_comparison_rules:
    mismatch_count = 0

    for order_id in sorted(json_order_ids & xml_order_ids):
        json_value = normalise_function(json_orders_by_id[order_id][json_field])
        xml_value = normalise_function(xml_orders_by_id[order_id][xml_field])

        if json_value != xml_value:
            mismatch_count += 1

    order_comparison_rows.append(
        {
            "target_field": target_field,
            "overlapping_keys_compared": len(json_order_ids & xml_order_ids),
            "mismatch_count": mismatch_count,
        }
    )

# Timestamps require source-specific parsing, so they are compared separately.
timestamp_mismatch_count = 0
for order_id in sorted(json_order_ids & xml_order_ids):
    json_value = normalise_timestamp_for_comparison(json_orders_by_id[order_id]["orderTimestamp"], "JSON")
    xml_value = normalise_timestamp_for_comparison(xml_orders_by_id[order_id]["Order_Timestamp"], "XML")
    if json_value != xml_value:
        timestamp_mismatch_count += 1

order_comparison_rows.append(
    {
        "target_field": "order_timestamp",
        "overlapping_keys_compared": len(json_order_ids & xml_order_ids),
        "mismatch_count": timestamp_mismatch_count,
    }
)

order_overlap_comparison = pd.DataFrame(order_comparison_rows)
display(order_overlap_comparison)
print("Total order-field mismatches:", int(order_overlap_comparison["mismatch_count"].sum()))


# **Observation and decision:** 1,100 overlapping orders were compared for every listed comparable field, and zero normalised mismatches were observed. Therefore, equal normalised values can be retained once. Any future different non-missing value will still be recorded as a conflict instead of a source being chosen silently.
# 

# ### 1.9 Normalised comparison of overlapping reviews
# 
# The same field-level approach is applied to reviews. Raw review text is compared here only to test source overlap; the full published text-cleaning contract belongs to the later text-processing task.
# 

# In[21]:


# Index both review sources by their stable review ID.
json_reviews_by_id = {record["reviewID"]: record for record in json_reviews}
xml_reviews_by_id = {record["Review_ID"]: record for record in xml_reviews}

# List each comparable target field and its source-specific field names.
review_comparison_rules = [
    ("order_id", "orderID", "Order_ID", normalise_text_for_comparison),
    ("order_item_id", "orderItemID", "Order_Item_ID", normalise_text_for_comparison),
    ("product_id", "productID", "Product_ID", normalise_text_for_comparison),
    ("customer_id", "customerID", "Customer_ID", normalise_text_for_comparison),
    ("language_code", "languageCode", "Language_Code", normalise_text_for_comparison),
    ("rating", "rating", "Rating", normalise_number_for_comparison),
    ("review_title", "reviewTitle", "Review_Title", normalise_text_for_comparison),
    ("verified_purchase", "verifiedPurchase", "Verified_Purchase", normalise_boolean_for_comparison),
    ("helpful_votes", "helpfulVotes", "Helpful_Votes", normalise_number_for_comparison),
    ("delivery_experience", "deliveryExperience", "Delivery_Experience", normalise_text_for_comparison),
    ("value_experience", "valueExperience", "Value_Experience", normalise_text_for_comparison),
    ("writing_style", "writingStyle", "Writing_Style", normalise_text_for_comparison),
    ("review_text_raw", "reviewText", "Review_Text", normalise_text_for_comparison),
]

# Compare every overlapping review one field at a time.
review_comparison_rows = []

for target_field, json_field, xml_field, normalise_function in review_comparison_rules:
    mismatch_count = 0

    for review_id in sorted(json_review_ids & xml_review_ids):
        json_value = normalise_function(json_reviews_by_id[review_id][json_field])
        xml_value = normalise_function(xml_reviews_by_id[review_id][xml_field])

        if json_value != xml_value:
            mismatch_count += 1

    review_comparison_rows.append(
        {
            "target_field": target_field,
            "overlapping_keys_compared": len(json_review_ids & xml_review_ids),
            "mismatch_count": mismatch_count,
        }
    )

# Timestamps require source-specific parsing, so they are compared separately.
review_timestamp_mismatch_count = 0
for review_id in sorted(json_review_ids & xml_review_ids):
    json_value = normalise_timestamp_for_comparison(json_reviews_by_id[review_id]["reviewTimestamp"], "JSON")
    xml_value = normalise_timestamp_for_comparison(xml_reviews_by_id[review_id]["Review_Timestamp"], "XML")
    if json_value != xml_value:
        review_timestamp_mismatch_count += 1

review_comparison_rows.append(
    {
        "target_field": "review_timestamp",
        "overlapping_keys_compared": len(json_review_ids & xml_review_ids),
        "mismatch_count": review_timestamp_mismatch_count,
    }
)

review_overlap_comparison = pd.DataFrame(review_comparison_rows)
display(review_overlap_comparison)
print("Total review-field mismatches:", int(review_overlap_comparison["mismatch_count"].sum()))


# **Observation and decision:** 1,260 overlapping reviews were compared for every listed comparable field, and zero normalised mismatches were observed. Therefore, one canonical review can be retained per stable key after normalisation while the same no-precedence conflict rule is kept.
# 

# ### 1.10 Source comparison and assumptions
# 
# The structural collection that supplies each target table is shown. The grain, candidate key, and reconciliation decisions are stated in markdown after the code output.
# 

# In[22]:


# Show source coverage only; grain and key decisions are documented below.
source_inventory = pd.DataFrame(
    [
        {"target_table": "orders", "JSON_source": "$.orderHeaders[*]", "XML_source": "/OperationsExport/Orders/Order/Header"},
        {"target_table": "order_items", "JSON_source": "", "XML_source": "/OperationsExport/Orders/Order/Shopping_Cart/Item"},
        {"target_table": "customers", "JSON_source": "", "XML_source": "/OperationsExport/Customers/Customer"},
        {"target_table": "deliveries", "JSON_source": "", "XML_source": "/OperationsExport/Orders/Order/Delivery"},
        {"target_table": "products", "JSON_source": "$.productCatalog[*]", "XML_source": ""},
        {"target_table": "product_reviews", "JSON_source": "$.productReviews[*]", "XML_source": "/OperationsExport/ProductReviews/Review"},
    ]
)

display(source_inventory)


# **Observation and decisions:**
# 
# - It was observed that orders and reviews occur in both sources. Their target grains are defined as one canonical order (`order_id`) and one canonical review (`review_id`), and they are reconciled by stable key.
# - It was observed that repeated order items, customers, and deliveries occur only in XML. Their target grains are defined as one order item (`order_item_id`), one customer (`customer_id`), and one completed-order delivery (`delivery_id`).
# - It was observed that products occur only in JSON. The target grain is defined as one product (`product_id`).
# - If different non-missing values are found for the same normalised field and key in a future comparison, a conflict will be recorded rather than JSON or XML being chosen silently.
# 

# ## 2. Source-to-target mapping
# 
# The official mapping is completed because it is the full field-lineage record. All 111 mapping IDs, target rows, and their order are preserved. `|` is used only when several input paths contribute to one target field.
# 
# The completed file is `Group018_source_to_target_mapping.csv`.
# 

# ### 2.1 Table-level mapping evidence
# 
# - **Orders:** Fields are mapped from both order-header structures, and a no-precedence conflict rule is used.
# - **Order items:** Repeated XML cart items are mapped at one-row-per-item grain.
# - **Customers:** XML customer elements are mapped at one-row-per-customer grain.
# - **Deliveries:** The XML delivery child is mapped while its order relationship is retained.
# - **Products:** JSON product-catalog records are mapped at one-row-per-product grain.
# - **Product reviews:** Both review sources are mapped, and fields derived from raw multilingual review text are identified.
# 

# In[23]:


# Load the completed mapping, untouched template and public dictionary.
mapping_path = Path(f"{GROUP_ID}_source_to_target_mapping.csv")
mapping_template_path = TEMPLATE_DIR / "A1_source_to_target_mapping_template.csv"

mapping = pd.read_csv(mapping_path, keep_default_na=False)
mapping_template = pd.read_csv(mapping_template_path, keep_default_na=False)
public_dictionary = pd.read_csv(DICTIONARY_PATH, keep_default_na=False)

print("Completed mapping rows:", len(mapping))
display(mapping.head())


# **Observation and decision:** The completed mapping contains 111 rows, matching the number of target fields in the public data dictionary. The official mapping IDs, table order, and target-field order are retained, and all required explanation columns are validated below.
# 

# ### 2.2 Mapping completeness checks
# 
# The completed mapping is validated against the official template and public data dictionary. This is done because a readable mapping can still be incomplete or out of order.
# 

# In[24]:


# Compare target rows with the public dictionary in their required order.
expected_pairs = list(zip(public_dictionary["output_table"], public_dictionary["field_name"]))
actual_pairs = list(zip(mapping["output_table"], mapping["target_field"]))

# These mapping explanations must be present on every row.
required_mapping_columns = [
    "source_format",
    "transformation_or_derivation",
    "overlap_or_conflict_rule",
    "notebook_evidence",
]

mapping_check_rows = []

mapping_check_rows.append({"check": "row count matches official template", "passed": len(mapping) == len(mapping_template), "observed": len(mapping)})
mapping_check_rows.append({"check": "mapping IDs unchanged", "passed": mapping["mapping_id"].tolist() == mapping_template["mapping_id"].tolist(), "observed": mapping["mapping_id"].nunique()})
mapping_check_rows.append({"check": "target rows match public dictionary order", "passed": actual_pairs == expected_pairs, "observed": len(actual_pairs)})
mapping_check_rows.append({"check": "mapping IDs unique", "passed": mapping["mapping_id"].is_unique, "observed": mapping["mapping_id"].nunique()})
mapping_check_rows.append({"check": "source formats allowed", "passed": mapping["source_format"].isin(["JSON", "XML", "both", "derived"]).all(), "observed": " | ".join(sorted(mapping["source_format"].unique()))})

# Count blank values in every required explanation column.
for column_name in required_mapping_columns:
    blank_count = int(mapping[column_name].eq("").sum())
    mapping_check_rows.append({"check": f"{column_name} is complete", "passed": blank_count == 0, "observed": f"{blank_count} blank"})

# Check that each source format has the structural path it requires.
json_path_problem = (
    mapping["source_format"].isin(["JSON", "both"])
    & mapping["json_source_path"].eq("")
).sum()
xml_path_problem = (
    mapping["source_format"].isin(["XML", "both"])
    & mapping["xml_source_path"].eq("")
).sum()
derived_without_input_path = (
    mapping["source_format"].eq("derived")
    & mapping["json_source_path"].eq("")
    & mapping["xml_source_path"].eq("")
).sum()

mapping_check_rows.append({"check": "JSON/both rows contain JSON paths", "passed": json_path_problem == 0, "observed": int(json_path_problem)})
mapping_check_rows.append({"check": "XML/both rows contain XML paths", "passed": xml_path_problem == 0, "observed": int(xml_path_problem)})
mapping_check_rows.append({"check": "derived rows identify at least one input path", "passed": derived_without_input_path == 0, "observed": int(derived_without_input_path)})

mapping_validation = pd.DataFrame(mapping_check_rows)
display(mapping_validation)
print("Passed mapping checks:", int(mapping_validation["passed"].sum()), "of", len(mapping_validation))

if not mapping_validation["passed"].all():
    raise ValueError("The completed mapping failed at least one completeness check.")


# **Observation and decision:** All mapping checks passed. It was observed that there are 111 unique mapping IDs, the same target-row order as the public dictionary, valid source-format values, complete transformation and conflict explanations, complete section references, and all required structural paths. Therefore, this CSV is retained as the Task 1 field-lineage record.
# 

# ## Task 1 conclusion
# 
# Both source files have been structurally parsed, their grains and relationships have been documented, formats and missing values have been profiled, candidate keys have been tested, duplication and overlap have been measured, and the official field mapping has been completed. This notebook now ends after Task 1 so that unfinished later-task placeholders cannot be confused with completed work.
# 

# ## 3. Task 2 - Relational transformation
# 
# Six interim relational tables are built in this section. The tables are built in dependency order so that child and parent relationships can be checked clearly. The 11 fields that require the published Task 3 text functions are intentionally omitted until those functions are implemented.
# 
# Each conversion is kept explicit. Helper fields are retained only in staging tables and are not written to the interim CSV files.
# 

# ### 3.1 Small normalisation functions
# 
# Separate functions are used for each source representation. This makes each conversion visible and prevents source-specific formats from being mixed together.
# 

# In[25]:


def normalise_identifier(value):
    """Return an identifier with surrounding whitespace removed."""
    return str(value).strip()


def normalise_string(value):
    """Return an ordinary string with surrounding whitespace removed."""
    return str(value).strip()


def normalise_optional_string(value):
    """Return a trimmed string or the literal string 'NaN' when it is empty."""
    if value is None:
        return "NaN"

    cleaned_value = str(value).strip()

    if cleaned_value == "":
        return "NaN"

    return cleaned_value


def parse_iso_date(value):
    """Convert an ISO source date to YYYY-MM-DD."""
    parsed_date = pd.to_datetime(value, format="%Y-%m-%d", errors="raise")
    return parsed_date.strftime("%Y-%m-%d")


def parse_day_first_date(value):
    """Convert a day-first source date to YYYY-MM-DD."""
    parsed_date = pd.to_datetime(value, format="%d/%m/%Y", errors="raise")
    return parsed_date.strftime("%Y-%m-%d")


def parse_iso_timestamp(value):
    """Convert an ISO source timestamp to YYYY-MM-DD HH:MM:SS."""
    parsed_timestamp = pd.to_datetime(value, format="%Y-%m-%d %H:%M:%S", errors="raise")
    return parsed_timestamp.strftime("%Y-%m-%d %H:%M:%S")


def parse_day_first_timestamp(value):
    """Convert a day-first source timestamp to YYYY-MM-DD HH:MM:SS."""
    parsed_timestamp = pd.to_datetime(value, format="%d/%m/%Y %H:%M:%S", errors="raise")
    return parsed_timestamp.strftime("%Y-%m-%d %H:%M:%S")


def parse_xml_boolean(value):
    """Convert an XML Y or N value to a Python boolean."""
    cleaned_value = str(value).strip().upper()

    if cleaned_value == "Y":
        return True

    if cleaned_value == "N":
        return False

    raise ValueError(f"Unexpected XML boolean value: {value}")


def parse_xml_currency(value):
    """Remove the XML currency label and separators, then return a number."""
    cleaned_value = str(value).replace("AUD", "").replace(",", "").strip()
    return float(cleaned_value)


def parse_xml_percentage(value):
    """Remove the XML percent sign and return numeric percentage points."""
    cleaned_value = str(value).replace("%", "").strip()
    return float(cleaned_value)


def parse_number(value):
    """Convert one source value to a number."""
    return float(str(value).replace(",", "").strip())


def values_match(first_value, second_value, tolerance=0.0):
    """Return True when two non-missing values agree within the given tolerance."""
    if tolerance > 0:
        return abs(float(first_value) - float(second_value)) <= tolerance

    return first_value == second_value


print("Normalisation functions prepared: 11")


# **Observation and decision:** Eleven small normalisation functions were prepared. A separate function was retained for each source-specific date, timestamp, boolean, currency, percentage and missing-string representation so that each conversion can be inspected independently.
# 

# ### 3.2 Build `order_items`
# 
# The repeated XML `Item` elements are converted first because their rounded line revenues are needed to calculate order prices. This follows `MAP-order_items-01` to `MAP-order_items-06`.
# 

# In[26]:


# Convert the parsed XML item dictionaries into a staging DataFrame.
xml_items_raw = pd.DataFrame(xml_items)
order_items_stage = pd.DataFrame()

# Create each target field separately.
order_items_stage["order_item_id"] = xml_items_raw["Order_Item_ID"].map(normalise_identifier)
order_items_stage["order_id"] = xml_items_raw["Order_ID"].map(normalise_identifier)
order_items_stage["product_id"] = xml_items_raw["Product_ID"].map(normalise_identifier)
order_items_stage["quantity"] = xml_items_raw["Quantity"].map(parse_number)
order_items_stage["unit_price"] = xml_items_raw["Unit_Price"].map(parse_xml_currency)

# Calculate line revenue from the normalised quantity and unit price.
order_items_stage["line_revenue"] = (
    order_items_stage["quantity"] * order_items_stage["unit_price"]
).round(2)

# Keep the supplied revenue only as evidence for the arithmetic comparison.
order_items_stage["source_line_revenue"] = xml_items_raw["Line_Revenue"].map(parse_xml_currency)
order_items_stage["line_revenue_difference"] = (
    order_items_stage["line_revenue"] - order_items_stage["source_line_revenue"]
).abs()

line_revenue_mismatches = int((order_items_stage["line_revenue_difference"] > 0.01).sum())

# Select only the six required Task 2 fields and sort deterministically.
order_item_columns = [
    "order_item_id",
    "order_id",
    "product_id",
    "quantity",
    "unit_price",
    "line_revenue",
]

order_items_table = order_items_stage[order_item_columns].copy()
order_items_table = order_items_table.sort_values("order_item_id", kind="stable").reset_index(drop=True)

print("Order-item rows created:", len(order_items_table))
print("Line-revenue mismatches above 0.01:", line_revenue_mismatches)
display(order_items_table.head())


# **Observation and decision:** 15,618 order-item rows were created from the repeated XML items. Zero calculated line revenues differed from the supplied values by more than 0.01. Therefore, the calculated and rounded `line_revenue` values were retained.
# 

# ### 3.3 Build `customers`
# 
# The XML customer records are converted at one-row-per-customer grain. All 20 fields are available directly from XML. This follows `MAP-customers-01` to `MAP-customers-20`.
# 

# In[27]:


# Convert the parsed XML customer dictionaries into a staging DataFrame.
xml_customers_raw = pd.DataFrame(xml_customers)
customers_table = pd.DataFrame()

# Create each customer field separately.
customers_table["customer_id"] = xml_customers_raw["Customer_ID"].map(normalise_identifier)
customers_table["signup_date"] = xml_customers_raw["Signup_Date"].map(parse_day_first_date)
customers_table["loyalty_tier"] = xml_customers_raw["Loyalty_Tier"].map(normalise_string)
customers_table["customer_segment"] = xml_customers_raw["Customer_Segment"].map(normalise_string)
customers_table["age_band"] = xml_customers_raw["Age_Band"].map(normalise_string)
customers_table["preferred_channel"] = xml_customers_raw["Preferred_Channel"].map(normalise_string)
customers_table["home_suburb"] = xml_customers_raw["Home_Suburb"].map(normalise_string)
customers_table["prior_12m_orders"] = xml_customers_raw["Prior_12M_Orders"].map(parse_number)
customers_table["lifetime_value_before_period"] = xml_customers_raw["Lifetime_Value_Before_Period"].map(parse_xml_currency)
customers_table["marketing_consent"] = xml_customers_raw["Marketing_Consent"].map(parse_xml_boolean)
customers_table["home_postcode"] = xml_customers_raw["Home_Postcode"].map(normalise_identifier)
customers_table["home_state"] = xml_customers_raw["Home_State"].map(normalise_string)
customers_table["home_country"] = xml_customers_raw["Home_Country"].map(normalise_string)
customers_table["preferred_language"] = xml_customers_raw["Preferred_Language"].map(normalise_string)
customers_table["acquisition_source"] = xml_customers_raw["Acquisition_Source"].map(normalise_string)
customers_table["account_status"] = xml_customers_raw["Account_Status"].map(normalise_string)
customers_table["preferred_device"] = xml_customers_raw["Preferred_Device"].map(normalise_string)
customers_table["email_domain"] = xml_customers_raw["Email_Domain"].map(normalise_string)
customers_table["household_size_band"] = xml_customers_raw["Household_Size_Band"].map(normalise_string)
customers_table["contact_frequency_preference"] = xml_customers_raw["Contact_Frequency_Preference"].map(normalise_string)

customers_table = customers_table.sort_values("customer_id", kind="stable").reset_index(drop=True)

print("Customer rows created:", len(customers_table))
print("Customer fields created:", len(customers_table.columns))
display(customers_table.head())


# **Observation and decision:** 500 customer rows and all 20 customer fields were created. The one-row-per-customer grain was retained, and no text-processing field was deferred in this table.
# 

# ### 3.4 Build `deliveries`
# 
# The XML delivery records are converted at one-row-per-completed-order-delivery grain. The raw delivery note is kept only in staging for Task 3. This follows `MAP-deliveries-01` to `MAP-deliveries-20`.
# 

# In[28]:


# Convert the parsed XML delivery dictionaries into a staging DataFrame.
xml_deliveries_raw = pd.DataFrame(xml_deliveries)
deliveries_stage = pd.DataFrame()

# Create each completed Task 2 delivery field separately.
deliveries_stage["delivery_id"] = xml_deliveries_raw["Delivery_ID"].map(normalise_identifier)
deliveries_stage["order_id"] = xml_deliveries_raw["Order_ID"].map(normalise_identifier)
deliveries_stage["dispatch_date"] = xml_deliveries_raw["Dispatch_Date"].map(parse_day_first_date)
deliveries_stage["promised_date"] = xml_deliveries_raw["Promised_Date"].map(parse_day_first_date)
deliveries_stage["delivered_date"] = xml_deliveries_raw["Delivered_Date"].map(parse_day_first_date)
deliveries_stage["carrier"] = xml_deliveries_raw["Carrier"].map(normalise_string)
deliveries_stage["service_level"] = xml_deliveries_raw["Service_Level"].map(normalise_string)
deliveries_stage["delivery_status"] = xml_deliveries_raw["Delivery_Status"].map(normalise_string)
deliveries_stage["delay_days"] = xml_deliveries_raw["Delay_Days"].map(parse_number)
deliveries_stage["on_time_in_full"] = xml_deliveries_raw["On_Time_In_Full"].map(parse_xml_boolean)
deliveries_stage["fulfilment_hours"] = xml_deliveries_raw["Fulfilment_Hours"].map(parse_number)
deliveries_stage["delivery_cost"] = xml_deliveries_raw["Delivery_Cost"].map(parse_xml_currency)
deliveries_stage["delay_reason"] = xml_deliveries_raw["Delay_Reason"].map(normalise_string)
deliveries_stage["promised_days"] = xml_deliveries_raw["Promised_Days"].map(parse_number)
deliveries_stage["tracking_event_count"] = xml_deliveries_raw["Tracking_Event_Count"].map(parse_number)
deliveries_stage["delivery_window"] = xml_deliveries_raw["Delivery_Window"].map(normalise_string)
deliveries_stage["shipping_distance_km"] = xml_deliveries_raw["Shipping_Distance_Km"].map(parse_number)
deliveries_stage["signature_required"] = xml_deliveries_raw["Signature_Required"].map(parse_xml_boolean)
deliveries_stage["estimated_carbon_kg"] = xml_deliveries_raw["Estimated_Carbon_Kg"].map(parse_number)

# Preserve the raw narrative for Task 3 without exporting it now.
deliveries_stage["delivery_note_raw"] = xml_deliveries_raw["Delivery_Note_Clean"].map(normalise_string)

delivery_columns = [
    "delivery_id",
    "order_id",
    "dispatch_date",
    "promised_date",
    "delivered_date",
    "carrier",
    "service_level",
    "delivery_status",
    "delay_days",
    "on_time_in_full",
    "fulfilment_hours",
    "delivery_cost",
    "delay_reason",
    "promised_days",
    "tracking_event_count",
    "delivery_window",
    "shipping_distance_km",
    "signature_required",
    "estimated_carbon_kg",
]

deliveries_table = deliveries_stage[delivery_columns].copy()
deliveries_table = deliveries_table.sort_values("delivery_id", kind="stable").reset_index(drop=True)

print("Delivery rows created:", len(deliveries_table))
print("Delivery fields created now:", len(deliveries_table.columns))
print("Delivery statuses:", sorted(deliveries_table["delivery_status"].unique()))
display(deliveries_table.head())


# **Observation and decision:** 5,000 delivery rows were created, and every row had the `Delivered` status. Nineteen Task 2 fields were retained. `delivery_note_clean` was omitted because its published cleaning rule belongs to Task 3.
# 

# ### 3.5 Build `products`
# 
# The JSON product catalogue is converted at one-row-per-product grain. The raw product description is kept only in staging for Task 3. This follows `MAP-products-01` to `MAP-products-21`.
# 

# In[29]:


# Convert the parsed JSON product records into a staging DataFrame.
json_products_raw = pd.DataFrame(json_products)
products_stage = pd.DataFrame()

# Create each completed Task 2 product field separately.
products_stage["product_id"] = json_products_raw["productID"].map(normalise_identifier)
products_stage["product_name"] = json_products_raw["productName"].map(normalise_string)
products_stage["category"] = json_products_raw["category"].map(normalise_string)
products_stage["brand"] = json_products_raw["brand"].map(normalise_string)
products_stage["unit_price"] = json_products_raw["unitPrice"].map(parse_number)
products_stage["unit_cost"] = json_products_raw["unitCost"].map(parse_number)
products_stage["launch_year"] = json_products_raw["launchYear"].map(parse_number)
products_stage["warranty_months"] = json_products_raw["warrantyMonths"].map(parse_number)
products_stage["weight_kg"] = json_products_raw["weightKg"].map(parse_number)
products_stage["product_sku"] = json_products_raw["productSku"].map(normalise_identifier)
products_stage["subcategory"] = json_products_raw["subcategory"].map(normalise_string)
products_stage["model_family"] = json_products_raw["modelFamily"].map(normalise_string)
products_stage["colour"] = json_products_raw["colour"].map(normalise_string)
products_stage["supplier_id"] = json_products_raw["supplierID"].map(normalise_identifier)
products_stage["supplier_country"] = json_products_raw["supplierCountry"].map(normalise_string)
products_stage["launch_date"] = json_products_raw["launchDate"].map(parse_iso_date)
products_stage["tax_category"] = json_products_raw["taxCategory"].map(normalise_string)
products_stage["package_type"] = json_products_raw["packageType"].map(normalise_string)
products_stage["recyclable_packaging"] = json_products_raw["recyclablePackaging"].astype(bool)
products_stage["active_flag"] = json_products_raw["activeFlag"].astype(bool)

# Preserve the raw narrative for Task 3 without exporting it now.
products_stage["product_description_raw"] = json_products_raw["productDescription"].map(normalise_string)

product_columns = [
    "product_id",
    "product_name",
    "category",
    "brand",
    "unit_price",
    "unit_cost",
    "launch_year",
    "warranty_months",
    "weight_kg",
    "product_sku",
    "subcategory",
    "model_family",
    "colour",
    "supplier_id",
    "supplier_country",
    "launch_date",
    "tax_category",
    "package_type",
    "recyclable_packaging",
    "active_flag",
]

products_table = products_stage[product_columns].copy()
products_table = products_table.sort_values("product_id", kind="stable").reset_index(drop=True)

print("Product rows created:", len(products_table))
print("Product fields created now:", len(products_table.columns))
display(products_table.head())


# **Observation and decision:** 1,000 product rows and 20 Task 2 fields were created. `product_description_clean` was omitted because its published cleaning rule belongs to Task 3.
# 

# ### 3.6 Normalise and reconcile `orders`
# 
# JSON and XML order headers are normalised into the same field names before they are compared. Equal overlapping values are retained once, and no source is given automatic precedence. This follows `MAP-orders-01` to `MAP-orders-23`.
# 

# In[30]:


# Convert parsed JSON and XML order headers into source DataFrames.
json_orders_raw = pd.DataFrame(json_orders)
xml_orders_raw = pd.DataFrame(xml_headers)

# Build the normalised JSON order staging table field by field.
json_orders_stage = pd.DataFrame()
json_orders_stage["order_id"] = json_orders_raw["orderID"].map(normalise_identifier)
json_orders_stage["source_system_record_id"] = json_orders_raw["sourceSystemRecordID"].map(normalise_identifier)
json_orders_stage["customer_id"] = json_orders_raw["customerID"].map(normalise_identifier)
json_orders_stage["order_timestamp"] = json_orders_raw["orderTimestamp"].map(parse_iso_timestamp)
json_orders_stage["sales_channel"] = json_orders_raw["salesChannel"].map(normalise_string)
json_orders_stage["payment_method"] = json_orders_raw["paymentMethod"].map(normalise_string)
json_orders_stage["currency"] = json_orders_raw["currency"].map(normalise_string)
json_orders_stage["nearest_warehouse"] = json_orders_raw["nearestWarehouse"].map(normalise_string)
json_orders_stage["order_status"] = json_orders_raw["orderStatus"].map(normalise_string)
json_orders_stage["delivery_charges"] = json_orders_raw["deliveryCharges"].map(parse_number)
json_orders_stage["coupon_code"] = json_orders_raw["couponCode"].map(normalise_optional_string)
json_orders_stage["coupon_discount"] = json_orders_raw["couponDiscount"].map(parse_number)
json_orders_stage["season"] = json_orders_raw["season"].map(normalise_string)
json_orders_stage["expedited_delivery"] = json_orders_raw["expeditedDelivery"].astype(bool)
json_orders_stage["customer_lat"] = json_orders_raw["customerLat"].map(parse_number)
json_orders_stage["customer_long"] = json_orders_raw["customerLong"].map(parse_number)
json_orders_stage["device_type"] = json_orders_raw["deviceType"].map(normalise_string)
json_orders_stage["referral_source"] = json_orders_raw["referralSource"].map(normalise_string)
json_orders_stage["customer_note_raw"] = json_orders_raw["customerNote"].map(normalise_string)
json_orders_stage["source_order_price"] = json_orders_raw["orderPrice"].map(parse_number)
json_orders_stage["source_tax_amount"] = json_orders_raw["taxAmount"].map(parse_number)
json_orders_stage["source_order_total"] = json_orders_raw["orderTotal"].map(parse_number)

# Build the normalised XML order staging table field by field.
xml_orders_stage = pd.DataFrame()
xml_orders_stage["order_id"] = xml_orders_raw["Order_ID"].map(normalise_identifier)
xml_orders_stage["source_system_record_id"] = xml_orders_raw["Source_System_Record_ID"].map(normalise_identifier)
xml_orders_stage["customer_id"] = xml_orders_raw["Customer_ID"].map(normalise_identifier)
xml_orders_stage["order_timestamp"] = xml_orders_raw["Order_Timestamp"].map(parse_day_first_timestamp)
xml_orders_stage["sales_channel"] = xml_orders_raw["Sales_Channel"].map(normalise_string)
xml_orders_stage["payment_method"] = xml_orders_raw["Payment_Method"].map(normalise_string)
xml_orders_stage["currency"] = xml_orders_raw["Currency"].map(normalise_string)
xml_orders_stage["nearest_warehouse"] = xml_orders_raw["Nearest_Warehouse"].map(normalise_string)
xml_orders_stage["order_status"] = xml_orders_raw["Order_Status"].map(normalise_string)
xml_orders_stage["delivery_charges"] = xml_orders_raw["Delivery_Charges"].map(parse_xml_currency)
xml_orders_stage["coupon_code"] = xml_orders_raw["Coupon_Code"].map(normalise_optional_string)
xml_orders_stage["coupon_discount"] = xml_orders_raw["Coupon_Discount"].map(parse_xml_percentage)
xml_orders_stage["season"] = xml_orders_raw["Season"].map(normalise_string)
xml_orders_stage["expedited_delivery"] = xml_orders_raw["Expedited_Delivery"].map(parse_xml_boolean)
xml_orders_stage["customer_lat"] = xml_orders_raw["Customer_Lat"].map(parse_number)
xml_orders_stage["customer_long"] = xml_orders_raw["Customer_Long"].map(parse_number)
xml_orders_stage["device_type"] = xml_orders_raw["Device_Type"].map(normalise_string)
xml_orders_stage["referral_source"] = xml_orders_raw["Referral_Source"].map(normalise_string)
xml_orders_stage["customer_note_raw"] = xml_orders_raw["Customer_Note"].map(normalise_string)
xml_orders_stage["source_order_price"] = xml_orders_raw["Order_Price"].map(parse_xml_currency)
xml_orders_stage["source_tax_amount"] = xml_orders_raw["Tax_Amount"].map(parse_xml_currency)
xml_orders_stage["source_order_total"] = xml_orders_raw["Order_Total"].map(parse_xml_currency)

print("Normalised JSON order rows:", len(json_orders_stage))
print("Normalised XML order rows:", len(xml_orders_stage))


# In[31]:


# Merge the two normalised order sources by the stable order key.
orders_merged = json_orders_stage.merge(
    xml_orders_stage,
    on="order_id",
    how="outer",
    suffixes=("_json", "_xml"),
    validate="one_to_one",
)

# List every field that must be compared and reconciled.
order_reconciliation_fields = [
    "source_system_record_id",
    "customer_id",
    "order_timestamp",
    "sales_channel",
    "payment_method",
    "currency",
    "nearest_warehouse",
    "order_status",
    "delivery_charges",
    "coupon_code",
    "coupon_discount",
    "season",
    "expedited_delivery",
    "customer_lat",
    "customer_long",
    "device_type",
    "referral_source",
    "customer_note_raw",
    "source_order_price",
    "source_tax_amount",
    "source_order_total",
]

# Monetary source fields use the published tolerance.
order_tolerances = {
    "delivery_charges": 0.01,
    "source_order_price": 0.01,
    "source_tax_amount": 0.01,
    "source_order_total": 0.01,
}

order_conflict_rows = []
orders_stage = pd.DataFrame()
orders_stage["order_id"] = orders_merged["order_id"]

# Compare one field at a time so every conflict rule remains visible.
for field_name in order_reconciliation_fields:
    json_column = f"{field_name}_json"
    xml_column = f"{field_name}_xml"
    tolerance = order_tolerances.get(field_name, 0.0)

    both_present = orders_merged[json_column].notna() & orders_merged[xml_column].notna()

    for row_index in orders_merged.index[both_present]:
        json_value = orders_merged.at[row_index, json_column]
        xml_value = orders_merged.at[row_index, xml_column]

        if not values_match(json_value, xml_value, tolerance):
            order_conflict_rows.append(
                {
                    "order_id": orders_merged.at[row_index, "order_id"],
                    "field": field_name,
                    "json_value": json_value,
                    "xml_value": xml_value,
                }
            )

    # A non-missing value is retained only after the comparison has been completed.
    orders_stage[field_name] = orders_merged[json_column].combine_first(orders_merged[xml_column])

order_conflicts = pd.DataFrame(order_conflict_rows)

print("Canonical order keys after reconciliation:", len(orders_stage))
print("Unresolved order conflicts:", len(order_conflicts))

if not order_conflicts.empty:
    display(order_conflicts.head())
    raise ValueError("Order reconciliation found different non-missing values.")


# **Observation and decision:** 1,100 JSON orders and 5,000 XML orders were normalised before reconciliation. The outer reconciliation retained 5,000 canonical order keys and found zero unresolved field conflicts. Therefore, overlapping equal values were retained once without applying source precedence.
# 

# ### 3.7 Calculate order arithmetic
# 
# Order arithmetic is calculated from the completed order-item table rather than copied from the supplied order headers. Each published arithmetic step is kept separate so the calculation can be audited.
# 

# In[32]:


# Sum the already-rounded line revenues for each order.
calculated_order_prices = (
    order_items_table.groupby("order_id", as_index=False)["line_revenue"]
    .sum()
    .rename(columns={"line_revenue": "order_price"})
)
calculated_order_prices["order_price"] = calculated_order_prices["order_price"].round(2)

# Add the calculated order price to the reconciled order headers.
orders_stage = orders_stage.merge(
    calculated_order_prices,
    on="order_id",
    how="left",
    validate="one_to_one",
)

# Calculate the included GST before applying the coupon discount.
orders_stage["tax_amount"] = (orders_stage["order_price"] / 11).round(2)

# Convert percentage points to a rate for the discount calculation.
orders_stage["discount_rate"] = orders_stage["coupon_discount"] / 100

# Apply the coupon discount to order price.
orders_stage["discounted_order_price"] = (
    orders_stage["order_price"] * (1 - orders_stage["discount_rate"])
)

# Add delivery charges and round the final total.
orders_stage["order_total"] = (
    orders_stage["discounted_order_price"] + orders_stage["delivery_charges"]
).round(2)

# Compare each calculated monetary field with its supplied source value.
orders_stage["order_price_difference"] = (
    orders_stage["order_price"] - orders_stage["source_order_price"]
).abs().round(2)
orders_stage["tax_amount_difference"] = (
    orders_stage["tax_amount"] - orders_stage["source_tax_amount"]
).abs().round(2)
orders_stage["order_total_difference"] = (
    orders_stage["order_total"] - orders_stage["source_order_total"]
).abs().round(2)

order_arithmetic_check = pd.DataFrame(
    [
        {
            "field": "order_price",
            "mismatches_above_0.01": int((orders_stage["order_price_difference"] > 0.01).sum()),
            "maximum_difference": orders_stage["order_price_difference"].max(),
        },
        {
            "field": "tax_amount",
            "mismatches_above_0.01": int((orders_stage["tax_amount_difference"] > 0.01).sum()),
            "maximum_difference": orders_stage["tax_amount_difference"].max(),
        },
        {
            "field": "order_total",
            "mismatches_above_0.01": int((orders_stage["order_total_difference"] > 0.01).sum()),
            "maximum_difference": orders_stage["order_total_difference"].max(),
        },
    ]
)

# Select the 21 fields completed before Task 3.
order_columns = [
    "order_id",
    "source_system_record_id",
    "customer_id",
    "order_timestamp",
    "sales_channel",
    "payment_method",
    "currency",
    "nearest_warehouse",
    "order_status",
    "order_price",
    "delivery_charges",
    "coupon_code",
    "coupon_discount",
    "tax_amount",
    "order_total",
    "season",
    "expedited_delivery",
    "customer_lat",
    "customer_long",
    "device_type",
    "referral_source",
]

orders_table = orders_stage[order_columns].copy()
orders_table = orders_table.sort_values("order_id", kind="stable").reset_index(drop=True)

print("Order rows created:", len(orders_table))
print("Order fields created now:", len(orders_table.columns))
display(order_arithmetic_check)


# **Observation and decision:** 5,000 order rows and 21 Task 2 fields were created. The calculated `order_price`, included `tax_amount`, and discounted `order_total` were compared with the supplied values. No mismatch exceeded the published tolerance of 0.01. `customer_note_clean` and `promo_code` were omitted until Task 3.
# 

# ### 3.8 Normalise and reconcile `product_reviews`
# 
# JSON and XML reviews are normalised before reconciliation by `review_id`. The raw review text is reconciled and retained only in staging for Task 3. This follows `MAP-product_reviews-01` to `MAP-product_reviews-21`.
# 

# In[33]:


# Convert parsed JSON and XML reviews into source DataFrames.
json_reviews_raw = pd.DataFrame(json_reviews)
xml_reviews_raw = pd.DataFrame(xml_reviews)

# Build the normalised JSON review staging table field by field.
json_reviews_stage = pd.DataFrame()
json_reviews_stage["review_id"] = json_reviews_raw["reviewID"].map(normalise_identifier)
json_reviews_stage["order_id"] = json_reviews_raw["orderID"].map(normalise_identifier)
json_reviews_stage["order_item_id"] = json_reviews_raw["orderItemID"].map(normalise_identifier)
json_reviews_stage["product_id"] = json_reviews_raw["productID"].map(normalise_identifier)
json_reviews_stage["customer_id"] = json_reviews_raw["customerID"].map(normalise_identifier)
json_reviews_stage["review_timestamp"] = json_reviews_raw["reviewTimestamp"].map(parse_iso_timestamp)
json_reviews_stage["language_code"] = json_reviews_raw["languageCode"].map(normalise_string)
json_reviews_stage["rating"] = json_reviews_raw["rating"].map(parse_number)
json_reviews_stage["review_title"] = json_reviews_raw["reviewTitle"].map(normalise_string)
json_reviews_stage["verified_purchase"] = json_reviews_raw["verifiedPurchase"].astype(bool)
json_reviews_stage["helpful_votes"] = json_reviews_raw["helpfulVotes"].map(parse_number)
json_reviews_stage["delivery_experience"] = json_reviews_raw["deliveryExperience"].map(normalise_string)
json_reviews_stage["value_experience"] = json_reviews_raw["valueExperience"].map(normalise_string)
json_reviews_stage["writing_style"] = json_reviews_raw["writingStyle"].map(normalise_string)
json_reviews_stage["review_text_raw"] = json_reviews_raw["reviewText"].map(normalise_string)

# Build the normalised XML review staging table field by field.
xml_reviews_stage = pd.DataFrame()
xml_reviews_stage["review_id"] = xml_reviews_raw["Review_ID"].map(normalise_identifier)
xml_reviews_stage["order_id"] = xml_reviews_raw["Order_ID"].map(normalise_identifier)
xml_reviews_stage["order_item_id"] = xml_reviews_raw["Order_Item_ID"].map(normalise_identifier)
xml_reviews_stage["product_id"] = xml_reviews_raw["Product_ID"].map(normalise_identifier)
xml_reviews_stage["customer_id"] = xml_reviews_raw["Customer_ID"].map(normalise_identifier)
xml_reviews_stage["review_timestamp"] = xml_reviews_raw["Review_Timestamp"].map(parse_day_first_timestamp)
xml_reviews_stage["language_code"] = xml_reviews_raw["Language_Code"].map(normalise_string)
xml_reviews_stage["rating"] = xml_reviews_raw["Rating"].map(parse_number)
xml_reviews_stage["review_title"] = xml_reviews_raw["Review_Title"].map(normalise_string)
xml_reviews_stage["verified_purchase"] = xml_reviews_raw["Verified_Purchase"].map(parse_xml_boolean)
xml_reviews_stage["helpful_votes"] = xml_reviews_raw["Helpful_Votes"].map(parse_number)
xml_reviews_stage["delivery_experience"] = xml_reviews_raw["Delivery_Experience"].map(normalise_string)
xml_reviews_stage["value_experience"] = xml_reviews_raw["Value_Experience"].map(normalise_string)
xml_reviews_stage["writing_style"] = xml_reviews_raw["Writing_Style"].map(normalise_string)
xml_reviews_stage["review_text_raw"] = xml_reviews_raw["Review_Text"].map(normalise_string)

print("Normalised JSON review rows:", len(json_reviews_stage))
print("Normalised XML review rows:", len(xml_reviews_stage))


# In[34]:


# Merge the two normalised review sources by the stable review key.
reviews_merged = json_reviews_stage.merge(
    xml_reviews_stage,
    on="review_id",
    how="outer",
    suffixes=("_json", "_xml"),
    validate="one_to_one",
)

review_reconciliation_fields = [
    "order_id",
    "order_item_id",
    "product_id",
    "customer_id",
    "review_timestamp",
    "language_code",
    "rating",
    "review_title",
    "verified_purchase",
    "helpful_votes",
    "delivery_experience",
    "value_experience",
    "writing_style",
    "review_text_raw",
]

review_conflict_rows = []
product_reviews_stage = pd.DataFrame()
product_reviews_stage["review_id"] = reviews_merged["review_id"]

# Compare one review field at a time before retaining a canonical value.
for field_name in review_reconciliation_fields:
    json_column = f"{field_name}_json"
    xml_column = f"{field_name}_xml"
    both_present = reviews_merged[json_column].notna() & reviews_merged[xml_column].notna()

    for row_index in reviews_merged.index[both_present]:
        json_value = reviews_merged.at[row_index, json_column]
        xml_value = reviews_merged.at[row_index, xml_column]

        if not values_match(json_value, xml_value):
            review_conflict_rows.append(
                {
                    "review_id": reviews_merged.at[row_index, "review_id"],
                    "field": field_name,
                    "json_value": json_value,
                    "xml_value": xml_value,
                }
            )

    product_reviews_stage[field_name] = reviews_merged[json_column].combine_first(
        reviews_merged[xml_column]
    )

review_conflicts = pd.DataFrame(review_conflict_rows)

if not review_conflicts.empty:
    display(review_conflicts.head())
    raise ValueError("Review reconciliation found different non-missing values.")

review_columns = [
    "review_id",
    "order_id",
    "order_item_id",
    "product_id",
    "customer_id",
    "review_timestamp",
    "language_code",
    "rating",
    "review_title",
    "verified_purchase",
    "helpful_votes",
    "delivery_experience",
    "value_experience",
    "writing_style",
]

product_reviews_table = product_reviews_stage[review_columns].copy()
product_reviews_table = product_reviews_table.sort_values("review_id", kind="stable").reset_index(drop=True)

print("Canonical review rows created:", len(product_reviews_table))
print("Review fields created now:", len(product_reviews_table.columns))
print("Unresolved review conflicts:", len(review_conflicts))
display(product_reviews_table.head())


# **Observation and decision:** 7,000 JSON reviews and 1,260 XML reviews were normalised before reconciliation. The reconciliation retained 7,000 canonical reviews and found zero unresolved field conflicts. Fourteen Task 2 fields were retained. The seven fields derived from cleaned review text were omitted until Task 3.
# 

# ## 4. Task 2 verification
# 
# The completed Task 2 fields are checked before export. These checks cover structure, keys, relationships, row flow, formats, ranges, arithmetic, overlap and temporal ordering. The complete 111-field schema is recorded separately as deferred rather than reported as passing.
# 

# In[35]:


# Keep all six interim tables together for consistent checks and export.
task2_tables = {
    "orders": orders_table,
    "order_items": order_items_table,
    "customers": customers_table,
    "deliveries": deliveries_table,
    "products": products_table,
    "product_reviews": product_reviews_table,
}

task2_primary_keys = {
    "orders": "order_id",
    "order_items": "order_item_id",
    "customers": "customer_id",
    "deliveries": "delivery_id",
    "products": "product_id",
    "product_reviews": "review_id",
}

deferred_task3_fields = {
    "orders": ["customer_note_clean", "promo_code"],
    "order_items": [],
    "customers": [],
    "deliveries": ["delivery_note_clean"],
    "products": ["product_description_clean"],
    "product_reviews": [
        "review_body_clean",
        "review_body_latin_analysis",
        "review_length_chars",
        "review_word_count",
        "contains_non_latin_script",
        "extracted_order_reference",
        "extracted_product_sku",
    ],
}

# Derive the expected interim column order from the public dictionary.
expected_interim_columns = {}

for table_name in task2_tables:
    dictionary_fields = public_dictionary.loc[
        public_dictionary["output_table"] == table_name,
        "field_name",
    ].tolist()

    expected_interim_columns[table_name] = [
        field_name
        for field_name in dictionary_fields
        if field_name not in deferred_task3_fields[table_name]
    ]

print("Implemented Task 2 fields:", sum(len(table.columns) for table in task2_tables.values()))
print("Deferred Task 3 fields:", sum(len(fields) for fields in deferred_task3_fields.values()))


# In[36]:


task2_check_rows = []


def record_task2_check(check_id, check_area, passed, observed):
    """Add one Task 2 check result to the in-notebook verification register."""
    task2_check_rows.append(
        {
            "check_id": check_id,
            "area": check_area,
            "status": "PASS" if passed else "FAIL",
            "observed": observed,
        }
    )


# Check implemented column presence and order for each table.
for table_name, table in task2_tables.items():
    expected_columns = expected_interim_columns[table_name]
    actual_columns = table.columns.tolist()
    record_task2_check(
        f"T2-SCHEMA-{table_name}",
        "implemented column order",
        actual_columns == expected_columns,
        f"{len(actual_columns)} implemented fields",
    )

# Check each primary key separately.
for table_name, primary_key in task2_primary_keys.items():
    table = task2_tables[table_name]
    missing_keys = int(table[primary_key].isna().sum() + table[primary_key].eq("").sum())
    duplicate_keys = int(table[primary_key].duplicated(keep=False).sum())
    keys_are_sorted = table[primary_key].is_monotonic_increasing
    record_task2_check(
        f"T2-PK-{table_name}",
        "primary key",
        missing_keys == 0 and duplicate_keys == 0 and keys_are_sorted,
        f"{missing_keys} missing, {duplicate_keys} duplicate rows, sorted={keys_are_sorted}",
    )

# Check source flow without hard-coding expected row counts.
source_flow_expectations = {
    "orders": len(set(json_orders_stage["order_id"]) | set(xml_orders_stage["order_id"])),
    "order_items": len(xml_items_raw),
    "customers": len(xml_customers_raw),
    "deliveries": len(xml_deliveries_raw),
    "products": len(json_products_raw),
    "product_reviews": len(set(json_reviews_stage["review_id"]) | set(xml_reviews_stage["review_id"])),
}

for table_name, expected_rows in source_flow_expectations.items():
    observed_rows = len(task2_tables[table_name])
    record_task2_check(
        f"T2-FLOW-{table_name}",
        "source row flow",
        observed_rows == expected_rows,
        f"{observed_rows} canonical rows from {expected_rows} source keys",
    )

# Record overlap and conflict handling explicitly.
record_task2_check(
    "T2-OVERLAP-orders",
    "order reconciliation",
    len(order_conflicts) == 0 and orders_table["order_id"].is_unique,
    f"{len(order_conflicts)} conflicts and {len(orders_table)} canonical keys",
)
record_task2_check(
    "T2-OVERLAP-reviews",
    "review reconciliation",
    len(review_conflicts) == 0 and product_reviews_table["review_id"].is_unique,
    f"{len(review_conflicts)} conflicts and {len(product_reviews_table)} canonical keys",
)

task2_verification = pd.DataFrame(task2_check_rows)
display(task2_verification)

if task2_verification["status"].eq("FAIL").any():
    raise ValueError("At least one Task 2 structure, key, flow or overlap check failed.")


# In[37]:


# Check every implemented field against its public-dictionary data type.
field_type_check_rows = []

for table_name, table in task2_tables.items():
    table_dictionary = public_dictionary[
        public_dictionary["output_table"] == table_name
    ]

    for dictionary_row in table_dictionary.itertuples(index=False):
        field_name = dictionary_row.field_name

        # Task 3 fields are not present in the interim tables.
        if field_name in deferred_task3_fields[table_name]:
            continue

        field_values = table[field_name]
        data_type = dictionary_row.data_type

        if data_type == "string":
            type_passed = field_values.map(lambda value: isinstance(value, str)).all()
        elif data_type == "number":
            type_passed = pd.api.types.is_numeric_dtype(field_values)
        elif data_type == "boolean":
            type_passed = field_values.isin([True, False]).all()
        elif data_type == "date":
            pd.to_datetime(field_values, format="%Y-%m-%d", errors="raise")
            type_passed = field_values.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all()
        elif data_type == "datetime":
            pd.to_datetime(field_values, format="%Y-%m-%d %H:%M:%S", errors="raise")
            type_passed = field_values.str.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}").all()
        else:
            type_passed = False

        field_type_check_rows.append(
            {
                "table": table_name,
                "field": field_name,
                "required_type": data_type,
                "passed": bool(type_passed),
            }
        )

task2_field_type_checks = pd.DataFrame(field_type_check_rows)
type_check_summary = (
    task2_field_type_checks.groupby("required_type", as_index=False)["passed"]
    .agg(fields_checked="size", fields_passed="sum")
)

print("Implemented fields checked against dictionary types:", len(task2_field_type_checks))
display(type_check_summary)

if not task2_field_type_checks["passed"].all():
    display(task2_field_type_checks[~task2_field_type_checks["passed"]])
    raise ValueError("At least one implemented field failed its dictionary type check.")


# In[38]:


# Define the eight required foreign-key relationships.
foreign_key_rules = [
    ("orders.customer_id", orders_table["customer_id"], customers_table["customer_id"]),
    ("order_items.order_id", order_items_table["order_id"], orders_table["order_id"]),
    ("order_items.product_id", order_items_table["product_id"], products_table["product_id"]),
    ("deliveries.order_id", deliveries_table["order_id"], orders_table["order_id"]),
    ("product_reviews.order_id", product_reviews_table["order_id"], orders_table["order_id"]),
    ("product_reviews.order_item_id", product_reviews_table["order_item_id"], order_items_table["order_item_id"]),
    ("product_reviews.product_id", product_reviews_table["product_id"], products_table["product_id"]),
    ("product_reviews.customer_id", product_reviews_table["customer_id"], customers_table["customer_id"]),
]

foreign_key_result_rows = []

for relationship_name, child_values, parent_values in foreign_key_rules:
    parent_key_set = set(parent_values)
    missing_child_values = int(child_values.isna().sum() + child_values.eq("").sum())
    orphan_values = sorted(set(child_values.dropna()) - parent_key_set)

    foreign_key_result_rows.append(
        {
            "relationship": relationship_name,
            "missing_child_values": missing_child_values,
            "orphan_keys": len(orphan_values),
            "status": "PASS" if missing_child_values == 0 and len(orphan_values) == 0 else "FAIL",
        }
    )

task2_foreign_key_checks = pd.DataFrame(foreign_key_result_rows)
display(task2_foreign_key_checks)

if task2_foreign_key_checks["status"].eq("FAIL").any():
    raise ValueError("At least one Task 2 foreign-key check failed.")


# In[39]:


# Check arithmetic and sensible numeric ranges separately.
range_check_rows = [
    {"check": "quantity is positive", "passed": order_items_table["quantity"].gt(0).all()},
    {"check": "unit price is non-negative", "passed": order_items_table["unit_price"].ge(0).all()},
    {"check": "delivery charges are non-negative", "passed": orders_table["delivery_charges"].ge(0).all()},
    {"check": "coupon discount is between 0 and 100", "passed": orders_table["coupon_discount"].between(0, 100).all()},
    {"check": "customer latitude is valid", "passed": orders_table["customer_lat"].between(-90, 90).all()},
    {"check": "customer longitude is valid", "passed": orders_table["customer_long"].between(-180, 180).all()},
    {"check": "review rating is between 1 and 5", "passed": product_reviews_table["rating"].between(1, 5).all()},
    {"check": "helpful votes are non-negative", "passed": product_reviews_table["helpful_votes"].ge(0).all()},
]

task2_range_checks = pd.DataFrame(range_check_rows)

arithmetic_passed = (
    line_revenue_mismatches == 0
    and order_arithmetic_check["mismatches_above_0.01"].eq(0).all()
)

print("Arithmetic checks passed:", arithmetic_passed)
display(task2_range_checks)

if not arithmetic_passed or not task2_range_checks["passed"].all():
    raise ValueError("At least one Task 2 arithmetic or range check failed.")


# In[40]:


# Convert comparable dates and timestamps only for temporal checks.
order_times = orders_table[["order_id", "order_timestamp"]].copy()
order_times["order_timestamp_check"] = pd.to_datetime(
    order_times["order_timestamp"],
    format="%Y-%m-%d %H:%M:%S",
    errors="raise",
)

delivery_times = deliveries_table[["order_id", "dispatch_date", "promised_date", "delivered_date"]].copy()
delivery_times["dispatch_date_check"] = pd.to_datetime(delivery_times["dispatch_date"], format="%Y-%m-%d", errors="raise")
delivery_times["promised_date_check"] = pd.to_datetime(delivery_times["promised_date"], format="%Y-%m-%d", errors="raise")
delivery_times["delivered_date_check"] = pd.to_datetime(delivery_times["delivered_date"], format="%Y-%m-%d", errors="raise")

order_delivery_times = order_times.merge(delivery_times, on="order_id", how="inner", validate="one_to_one")

order_before_dispatch = (
    order_delivery_times["order_timestamp_check"].dt.normalize()
    <= order_delivery_times["dispatch_date_check"]
).all()
dispatch_before_delivery = (
    order_delivery_times["dispatch_date_check"]
    <= order_delivery_times["delivered_date_check"]
).all()
order_before_promised = (
    order_delivery_times["order_timestamp_check"].dt.normalize()
    <= order_delivery_times["promised_date_check"]
).all()

review_times = product_reviews_table[["review_id", "order_id", "review_timestamp"]].copy()
review_times["review_timestamp_check"] = pd.to_datetime(
    review_times["review_timestamp"],
    format="%Y-%m-%d %H:%M:%S",
    errors="raise",
)
review_order_times = review_times.merge(
    order_times[["order_id", "order_timestamp_check"]],
    on="order_id",
    how="left",
    validate="many_to_one",
)
review_after_order = (
    review_order_times["review_timestamp_check"]
    >= review_order_times["order_timestamp_check"]
).all()

task2_temporal_checks = pd.DataFrame(
    [
        {"check": "order date is not after dispatch date", "passed": order_before_dispatch},
        {"check": "dispatch date is not after delivered date", "passed": dispatch_before_delivery},
        {"check": "order date is not after promised date", "passed": order_before_promised},
        {"check": "review timestamp is not before order timestamp", "passed": review_after_order},
    ]
)

display(task2_temporal_checks)

if not task2_temporal_checks["passed"].all():
    raise ValueError("At least one Task 2 temporal check failed.")


# **Observation and decision:** All completed Task 2 structure, primary-key, foreign-key, row-flow, overlap, arithmetic, range and temporal checks passed. The checks were calculated from the source and interim tables rather than from hard-coded canonical answers.
# 

# In[41]:


# Record completion separately from the deferred Task 3 schema work.
task2_readiness = pd.DataFrame(
    [
        {
            "area": "completed Task 2 relational and arithmetic work",
            "status": "PASS",
            "observed": "All executable Task 2 checks passed",
        },
        {
            "area": "Task 3-dependent fields",
            "status": "DEFERRED",
            "observed": "11 fields have not been created",
        },
        {
            "area": "complete 111-field submission schema",
            "status": "NOT SUBMISSION READY",
            "observed": "100 of 111 fields are currently available",
        },
    ]
)

display(task2_readiness)


# ### Task 3 completed
# 
# All eleven Task 3-dependent fields have been added in the section below. The six CSV files have been regenerated as final, complete outputs with all 111 required fields.

# ## 5. Export the six interim CSV files
# 
# Only the six required filenames are written. Helper fields, conflict tables and verification tables remain inside the notebook.
# 

# In[42]:


# Define each required output path explicitly.
orders_output_path = OUTPUT_DIR / f"{GROUP_ID}_orders_standardised.csv"
order_items_output_path = OUTPUT_DIR / f"{GROUP_ID}_order_items_standardised.csv"
customers_output_path = OUTPUT_DIR / f"{GROUP_ID}_customers_standardised.csv"
deliveries_output_path = OUTPUT_DIR / f"{GROUP_ID}_deliveries_standardised.csv"
products_output_path = OUTPUT_DIR / f"{GROUP_ID}_products_standardised.csv"
product_reviews_output_path = OUTPUT_DIR / f"{GROUP_ID}_product_reviews_standardised.csv"

# Write one interim table at a time with no index column.
orders_table.to_csv(orders_output_path, index=False, encoding="utf-8")
order_items_table.to_csv(order_items_output_path, index=False, encoding="utf-8")
customers_table.to_csv(customers_output_path, index=False, encoding="utf-8")
deliveries_table.to_csv(deliveries_output_path, index=False, encoding="utf-8")
products_table.to_csv(products_output_path, index=False, encoding="utf-8")
product_reviews_table.to_csv(product_reviews_output_path, index=False, encoding="utf-8")

exported_paths = [
    orders_output_path,
    order_items_output_path,
    customers_output_path,
    deliveries_output_path,
    products_output_path,
    product_reviews_output_path,
]

print("Interim CSV files written:", len(exported_paths))

for exported_path in exported_paths:
    print(exported_path)


# ### 5.1 Re-read the exported CSV files
# 
# The exported files are read back with `keep_default_na=False`. This confirms that the written row counts and implemented column order agree with the in-memory tables.
# 

# In[43]:


# Re-read each exported file without converting the literal NaN string.
reloaded_task2_tables = {
    "orders": pd.read_csv(orders_output_path, keep_default_na=False),
    "order_items": pd.read_csv(order_items_output_path, keep_default_na=False),
    "customers": pd.read_csv(customers_output_path, keep_default_na=False),
    "deliveries": pd.read_csv(deliveries_output_path, keep_default_na=False),
    "products": pd.read_csv(products_output_path, keep_default_na=False),
    "product_reviews": pd.read_csv(product_reviews_output_path, keep_default_na=False),
}

reload_check_rows = []

for table_name, reloaded_table in reloaded_task2_tables.items():
    original_table = task2_tables[table_name]
    row_count_matches = len(reloaded_table) == len(original_table)
    column_order_matches = reloaded_table.columns.tolist() == original_table.columns.tolist()

    reload_check_rows.append(
        {
            "table": table_name,
            "rows": len(reloaded_table),
            "row_count_matches": row_count_matches,
            "column_order_matches": column_order_matches,
        }
    )

task2_reload_checks = pd.DataFrame(reload_check_rows)
display(task2_reload_checks)

if not task2_reload_checks[["row_count_matches", "column_order_matches"]].all().all():
    raise ValueError("At least one exported Task 2 CSV failed the re-read check.")


# **Observation and decision:** Six interim CSV files were written and read back successfully. Their row counts and implemented column order matched the in-memory tables. The files remain incomplete until Task 3 adds the 11 deferred fields.
# 
# ## Task 2 conclusion
# 
# The six relational grains, completed target fields, arithmetic rules and multi-source reconciliation have been implemented. All completed Task 2 checks passed. The interim outputs are not submission-ready because the Task 3 text-derived fields have not yet been created.
# 

# ## 6. Task 3 - Regex and multilingual text preprocessing
# 
# Task 2 produced 100 of the required 111 target fields. The eleven fields that
# depend on narrative-text cleaning and reference extraction were deliberately
# deferred, since Task 1's structured JSON/XML parsers must not be replaced by
# regex. The raw narrative values (`customer_note_raw`, `delivery_note_raw`,
# `product_description_raw`, `review_text_raw`) were instead preserved inside
# the existing staging DataFrames without being exported.
# 
# This section:
# - imports the six fixed functions from `Group018_text_functions.py`
#   (`clean_narrative_text`, `extract_order_reference`, `extract_product_sku`,
#   `extract_promo_code`, `build_latin_analysis`, `contains_non_latin_script`);
# - reuses the completed Task 2 staging DataFrames `orders_stage`,
#   `deliveries_stage`, `products_stage`, and `product_reviews_stage` -- no
#   JSON/XML is re-parsed here;
# - derives the eleven deferred fields, following the published order:
#   reference extraction on the raw value first, then decode/clean, then
#   Latin-script analysis built from the cleaned (not raw) text;
# - runs the supplied public text-function test cases together with additional
#   student-designed cases; and
# - rebuilds and re-exports all six standardised CSV files with the complete
#   111-field schema.

# In[44]:


from Group018_text_functions import (
    clean_narrative_text, extract_order_reference, extract_product_sku,
    extract_promo_code, build_latin_analysis, contains_non_latin_script,
)

# --- orders: +2 fields ---
orders_stage["customer_note_clean"] = orders_stage["customer_note_raw"].apply(clean_narrative_text)
orders_stage["promo_code"] = orders_stage["customer_note_raw"].apply(extract_promo_code)
order_columns_final = order_columns + ["customer_note_clean", "promo_code"]
orders_table = orders_stage[order_columns_final].copy()
orders_table = orders_table.sort_values("order_id", kind="stable").reset_index(drop=True)

# --- deliveries: +1 field ---
deliveries_stage["delivery_note_clean"] = deliveries_stage["delivery_note_raw"].apply(clean_narrative_text)
delivery_columns_final = delivery_columns + ["delivery_note_clean"]
deliveries_table = deliveries_stage[delivery_columns_final].copy()
deliveries_table = deliveries_table.sort_values("delivery_id", kind="stable").reset_index(drop=True)

# --- products: +1 field ---
products_stage["product_description_clean"] = products_stage["product_description_raw"].apply(clean_narrative_text)
product_columns_final = product_columns + ["product_description_clean"]
products_table = products_stage[product_columns_final].copy()
products_table = products_table.sort_values("product_id", kind="stable").reset_index(drop=True)

# --- product_reviews: +7 fields (new fields are interleaved, not appended) ---
raw = product_reviews_stage["review_text_raw"]
product_reviews_stage["extracted_order_reference"] = raw.apply(extract_order_reference)
product_reviews_stage["extracted_product_sku"] = raw.apply(extract_product_sku)
product_reviews_stage["review_body_clean"] = raw.apply(clean_narrative_text)

clean = product_reviews_stage["review_body_clean"]
product_reviews_stage["review_body_latin_analysis"] = clean.apply(build_latin_analysis)
product_reviews_stage["contains_non_latin_script"] = clean.apply(contains_non_latin_script)
product_reviews_stage["review_length_chars"] = clean.apply(lambda t: 0 if t == "NaN" else len(t))
product_reviews_stage["review_word_count"] = clean.apply(lambda t: 0 if t == "NaN" else len(t.split()))

review_columns_final = [
    "review_id","order_id","order_item_id","product_id","customer_id","review_timestamp","language_code",
    "rating","review_title","review_body_clean","review_body_latin_analysis","verified_purchase",
    "helpful_votes","review_length_chars","review_word_count","contains_non_latin_script",
    "extracted_order_reference","extracted_product_sku","delivery_experience","value_experience","writing_style",
]
product_reviews_table = product_reviews_stage[review_columns_final].copy()
product_reviews_table = product_reviews_table.sort_values("review_id", kind="stable").reset_index(drop=True)

# --- fresh dict for final validation/export ---
final_tables = {
    "orders": orders_table, "order_items": order_items_table, "customers": customers_table,
    "deliveries": deliveries_table, "products": products_table, "product_reviews": product_reviews_table,
}

for table_name, table in final_tables.items():
    expected_cols = public_dictionary.loc[public_dictionary["output_table"] == table_name, "field_name"].tolist()
    assert list(table.columns) == expected_cols, f"{table_name} column mismatch vs public dictionary"
print("All six tables match the complete public dictionary field order.")

for table_name, table in final_tables.items():
    path = OUTPUT_DIR / f"{GROUP_ID}_{table_name}_standardised.csv"
    table.to_csv(path, index=False, encoding="utf-8")
print("Final CSVs written:", len(final_tables))


# In[45]:


public_text_cases_path = Path("templates/A1_public_text_test_cases.csv")  
public_text_cases = pd.read_csv(public_text_cases_path, keep_default_na=False)
print("Columns:", list(public_text_cases.columns))
display(public_text_cases.head(10))


# In[46]:


FUNCTION_LOOKUP = {
    "clean_narrative_text": clean_narrative_text,
    "extract_order_reference": extract_order_reference,
    "extract_product_sku": extract_product_sku,
    "extract_promo_code": extract_promo_code,
    "build_latin_analysis": build_latin_analysis,
    "contains_non_latin_script": contains_non_latin_script,
}

public_test_rows = []
for _, row in public_text_cases.iterrows():
    func = FUNCTION_LOOKUP[row["function"]]
    actual = func(row["input_value"])
    expected = row["expected_output"]
    # contains_non_latin_script returns a real bool; the CSV stores it as text
    expected_cmp = (expected == "True") if row["function"] == "contains_non_latin_script" else expected
    public_test_rows.append({
        "case_id": row["case_id"],
        "function": row["function"],
        "purpose": row["purpose"],
        "expected": expected,
        "actual": actual,
        "status": "PASS" if actual == expected_cmp else "FAIL",
    })

public_test_results = pd.DataFrame(public_test_rows)
display(public_test_results)
print("Public cases passed:", (public_test_results["status"] == "PASS").sum(), "of", len(public_test_results))

if (public_test_results["status"] == "FAIL").any():
    display(public_test_results[public_test_results["status"] == "FAIL"])
    raise ValueError("At least one public text test case failed.")


# In[47]:


text_function_check_rows = []

def record_text_check(check_id, description, actual, expected):
    """Add one student-designed text-function check to the register."""
    text_function_check_rows.append({
        "check_id": check_id,
        "description": description,
        "actual": actual,
        "expected": expected,
        "status": "PASS" if actual == expected else "FAIL",
    })

record_text_check("TXT-CLEAN-01", "full pipeline strips markers/tags/emoji/entities/wrapper",
    clean_narrative_text("[VERIFIED_PURCHASE] Great phone!! \U0001F60A Reference: HORD123456 | SKU: SKU-ABC123 #verified-buyer Visit http://example.com PROMO: B1SAVE-14 [RATING: 5/5] [SOURCE: catalogue-import] <b>Bold</b> claim &amp; more   spacing"),
    "great phone!! visit bold claim & more spacing")
record_text_check("TXT-CLEAN-02", "None input returns sentinel", clean_narrative_text(None), "NaN")
record_text_check("TXT-CLEAN-03", "empty string returns sentinel", clean_narrative_text(""), "NaN")
record_text_check("TXT-CLEAN-04", "markers-only text returns sentinel", clean_narrative_text("[SYSTEM] [CATALOGUE] #verified-buyer"), "NaN")
record_text_check("TXT-CLEAN-05", "tags removed, content kept", clean_narrative_text("<p>Nice <i>item</i></p>"), "nice item")
record_text_check("TXT-CLEAN-06", "multilingual letters preserved", clean_narrative_text("Amazing quality! 很好用 Très bien"), "amazing quality! 很好用 très bien")

record_text_check("TXT-ORDREF-01", "matched HORD", extract_order_reference("Order was HORD123456 great"), "HORD123456")
record_text_check("TXT-ORDREF-02", "matched CORD lower-case input", extract_order_reference("ref cord998877 here"), "CORD998877")
record_text_check("TXT-ORDREF-03", "embedded near-match rejected", extract_order_reference("XHORD123456"), "NaN")
record_text_check("TXT-ORDREF-04", "overlong near-match rejected", extract_order_reference("HORD1234567"), "NaN")
record_text_check("TXT-ORDREF-05", "too-short near-match rejected", extract_order_reference("HORD12345"), "NaN")
record_text_check("TXT-ORDREF-06", "absent reference returns sentinel", extract_order_reference("no reference here"), "NaN")
record_text_check("TXT-ORDREF-07", "None input returns sentinel", extract_order_reference(None), "NaN")

record_text_check("TXT-SKU-01", "matched SKU", extract_product_sku("item SKU-ABC123 in stock"), "SKU-ABC123")
record_text_check("TXT-SKU-02", "embedded near-match rejected", extract_product_sku("XSKU-ABC123"), "NaN")
record_text_check("TXT-SKU-03", "absent SKU returns sentinel", extract_product_sku("no sku here"), "NaN")

record_text_check("TXT-PROMO-01", "matched B1SAVE", extract_promo_code("use code B1SAVE-14 today"), "B1SAVE-14")
record_text_check("TXT-PROMO-02", "matched B5SAVE upper bound", extract_promo_code("B5SAVE-09"), "B5SAVE-09")
record_text_check("TXT-PROMO-03", "out-of-range B6SAVE rejected", extract_promo_code("B6SAVE-14"), "NaN")
record_text_check("TXT-PROMO-04", "three-digit code rejected", extract_promo_code("B1SAVE-145"), "NaN")
record_text_check("TXT-PROMO-05", "embedded near-match rejected", extract_promo_code("XB1SAVE-14"), "NaN")
record_text_check("TXT-PROMO-06", "absent promo code returns sentinel", extract_promo_code("no promo here"), "NaN")

record_text_check("TXT-LATIN-01", "keeps Latin + diacritics, drops CJK letters",
    build_latin_analysis("amazing quality! 很好用 très bien é"), "amazing quality! très bien é")
record_text_check("TXT-LATIN-02", "all non-Latin letters returns sentinel", build_latin_analysis("很好用"), "NaN")
record_text_check("TXT-LATIN-03", "sentinel input passes through", build_latin_analysis("NaN"), "NaN")
record_text_check("TXT-LATIN-04", "Arabic diacritics stripped, not just base letters",
    build_latin_analysis(clean_narrative_text("مَرْحَبًا vela spark 603 has a great screen")),
    "vela spark 603 has a great screen")
record_text_check("TXT-LATIN-05", "orphaned punctuation from removed non-Latin words dropped",
    build_latin_analysis(clean_narrative_text("candle shift 898 को मैंने कमजोर, सिग्नल, candle shift 898")),
    "candle shift 898 candle shift 898")

record_text_check("TXT-SCRIPT-01", "mixed script detected as True", contains_non_latin_script("très bien 很好用"), True)
record_text_check("TXT-SCRIPT-02", "pure Latin detected as False", contains_non_latin_script("very good, fast."), False)
record_text_check("TXT-SCRIPT-03", "sentinel input detected as False", contains_non_latin_script("NaN"), False)
record_text_check("TXT-SCRIPT-04", "Cyrillic detected as True", contains_non_latin_script("Привет мир"), True)

text_function_checks = pd.DataFrame(text_function_check_rows)
display(text_function_checks)

if text_function_checks["status"].eq("FAIL").any():
    raise ValueError("At least one student-designed text-function check failed.")


# In[50]:


reloaded_final_tables = {
    name: pd.read_csv(OUTPUT_DIR / f"{GROUP_ID}_{name}_standardised.csv", keep_default_na=False)
    for name in final_tables
}

for name, table in final_tables.items():
    reloaded = reloaded_final_tables[name]
    assert len(reloaded) == len(table), f"{name} row count mismatch after reload"
    assert list(reloaded.columns) == list(table.columns), f"{name} column order mismatch after reload"

print("All six final CSVs re-read successfully with matching row counts and column order.")


# **Observation and decision:** All eleven deferred fields were created and
# inserted into their public-dictionary positions. All supplied public
# text-function test cases passed, and all student-designed matched,
# unmatched, missing, multilingual and near-match cases passed. The six
# standardised CSV files were regenerated with the complete 111-field schema
# and re-read successfully with matching row counts and column order.
# 
# ## Task 3 conclusion
# 
# The eleven Task 3-dependent fields have been derived using the six fixed
# functions in `Group018_text_functions.py`, following the published
# extraction-before-cleaning order, the multilingual preservation contract,
# and the literal `NaN` sentinel convention. All public and student-designed
# text-function tests passed, and the six relational tables now contain the
# complete 111-field public-dictionary schema.

# In[ ]:




