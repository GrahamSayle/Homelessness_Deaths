#### Preamble ####
# Purpose: Tests the cleaned dataset on the cause of death of people
# experiencing homelessness in Toronto against the raw resource it was
# built from.
# Author: Graham Sayle
# Date: 27 September 2026
# Contact: g.sayle@mail.utoronto.ca
# License: MIT
# Pre-requisites:
# - `polars` must be installed (pip install polars)
# - 02-download_data.R must have been run
# - 03-clean_data.py must have been run


#### Workspace setup ####
import sys
from pathlib import Path

import polars as pl

RAW_PATH = Path("data/01-raw_data/raw_data.csv")
ANALYSIS_PATH = Path("data/02-analysis_data/analysis_data.csv")


#### Expected values ####

YEARS = [2022, 2023, 2024]

CAUSES = [
    "Acute Drug Toxicity",
    "Cardiovascular Disease",
    "Homicide",
    "Other Diseases",
    "Pending",
    "Suicide",
    "Unintentional Injury",
    "Unknown",
]
AGE_GROUPS = ["<20", "20-39", "40-59", "60+", "Unknown"]
GENDERS = ["Female", "Male", "Unknown"]

# the age column is renamed during cleaning, so raw and cleaned data use
# different names for the same thing
RAW_AGE_COLUMN = "Final_Age (group)"
CLEAN_AGE_COLUMN = "age_group"

EXPECTED_RAW_DTYPES = {
    "_id": pl.Int64,
    "Year of death": pl.Int64,
    "Subgroup": pl.Utf8,
    RAW_AGE_COLUMN: pl.Utf8,
    "Gender": pl.Utf8,
    "Count": pl.Utf8,  # holds "Suppressed" alongside numeric strings
}

NUMERIC_DTYPES = {pl.Int64, pl.Int32, pl.Float64, pl.Float32}


#### Load data ####
def load_data():
    if not RAW_PATH.exists():
        print(f"FAIL  no raw data found at {RAW_PATH}")
        print("      run 01-download_data.R first")
        sys.exit(1)

    if not ANALYSIS_PATH.exists():
        print(f"FAIL  no analysis data found at {ANALYSIS_PATH}")
        print("      run 02-clean_data.py first")
        sys.exit(1)

    raw_data = pl.read_csv(RAW_PATH)
    analysis_data = pl.read_csv(ANALYSIS_PATH)
    return raw_data, analysis_data


#### Test 1: expected columns are present, with the right types ####
def test_schema(raw_data, analysis_data):
    failures = []

    # raw data: every expected column present with the expected type
    for col, expected_dtype in EXPECTED_RAW_DTYPES.items():
        if col not in raw_data.columns:
            failures.append(f"raw data is missing column '{col}'")
            continue
        actual_dtype = raw_data.schema[col]
        if actual_dtype != expected_dtype:
            failures.append(
                f"raw data column '{col}' has type {actual_dtype}, "
                f"expected {expected_dtype}"
            )

    # cleaned data: the same columns, except the age column is renamed
    # during cleaning, and is_suppressed is added
    expected_analysis_columns = (
        (set(EXPECTED_RAW_DTYPES) - {RAW_AGE_COLUMN})
        | {CLEAN_AGE_COLUMN, "is_suppressed"}
    )
    missing = expected_analysis_columns - set(analysis_data.columns)
    if missing:
        failures.append(f"analysis data is missing columns: {sorted(missing)}")
        return failures

    if RAW_AGE_COLUMN in analysis_data.columns:
        failures.append(
            f"analysis data still has the raw column name '{RAW_AGE_COLUMN}'; "
            f"expected it to be renamed to '{CLEAN_AGE_COLUMN}' during cleaning"
        )

    if analysis_data.schema["is_suppressed"] != pl.Boolean:
        failures.append(
            f"analysis data column 'is_suppressed' has type "
            f"{analysis_data.schema['is_suppressed']}, expected Boolean"
        )

    if analysis_data.schema["Count"] not in NUMERIC_DTYPES:
        failures.append(
            f"analysis data column 'Count' has type {analysis_data.schema['Count']}, "
            f"expected a numeric type (cleaning should convert it from text)"
        )

    for col in ["Subgroup", CLEAN_AGE_COLUMN, "Gender"]:
        if analysis_data.schema[col] != pl.Utf8:
            failures.append(
                f"analysis data column '{col}' has type {analysis_data.schema[col]}, "
                f"expected Utf8"
            )

    if analysis_data.schema["Year of death"] != pl.Int64:
        failures.append(
            f"analysis data column 'Year of death' has type "
            f"{analysis_data.schema['Year of death']}, expected Int64"
        )

    return failures


#### Test 2: every described category actually appears ####
def test_values_present(analysis_data):
    failures = []

    expected_by_column = {
        "Subgroup": CAUSES,
        CLEAN_AGE_COLUMN: AGE_GROUPS,
        "Gender": GENDERS,
        "Year of death": YEARS,
    }

    for col, expected in expected_by_column.items():
        observed = set(analysis_data[col].drop_nulls().to_list())
        expected_set = set(expected)

        unexpected = sorted(observed - expected_set, key=str)
        if unexpected:
            failures.append(f"column '{col}' has values not in the expected set: {unexpected}")

        absent = sorted(expected_set - observed, key=str)
        if absent:
            failures.append(f"column '{col}' is missing expected values: {absent}")

    return failures


#### Test 3: a cell is flagged suppressed only when its count is missing ####
def test_suppression_flag(raw_data, analysis_data):
    failures = []

    # within the cleaned data: is_suppressed and "Count is null" must agree
    # in both directions, row for row
    mismatched = analysis_data.filter(
        pl.col("is_suppressed") != pl.col("Count").is_null()
    )
    if mismatched.height > 0:
        failures.append(
            f"{mismatched.height} rows have is_suppressed that disagrees with "
            f"whether Count is missing"
        )

    # against the raw data: the number of cells the portal marked "Suppressed"
    # should equal the number flagged is_suppressed after cleaning
    n_suppressed_raw = raw_data.filter(pl.col("Count") == "Suppressed").height
    n_suppressed_clean = analysis_data.filter(pl.col("is_suppressed")).height

    if n_suppressed_raw != n_suppressed_clean:
        failures.append(
            f"{n_suppressed_raw} cells are marked 'Suppressed' in the raw data, "
            f"but {n_suppressed_clean} are flagged is_suppressed after cleaning"
        )

    return failures

#### Run tests ####
def main():
    raw_data, analysis_data = load_data()

    tests = [
        ("Expected columns are present, with the right types", test_schema),
        ("All described category values are present", test_values_present),
        ("A cell is flagged suppressed only when its count is missing", test_suppression_flag),
    ]

    all_passed = True

    for name, test in tests:
        try:
            if test is test_values_present:
                failures = test(analysis_data)
            else:
                failures = test(raw_data, analysis_data)
        except Exception as error:  # a crashing test is a failing test
            failures = [f"test raised {type(error).__name__}: {error}"]

        if failures:
            all_passed = False
            print(f"FAIL  {name}")
            for failure in failures:
                print(f"      - {failure}")
        else:
            print(f"PASS  {name}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()