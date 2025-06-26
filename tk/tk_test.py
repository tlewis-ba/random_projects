#!/usr/bin/env python3

"Test timekeeping"

from datetime import date
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest
from tk import (compute_time_gap_hours, debug, expand_month_string,
                filter_work_entries_by_date, parse_date_string,
                parse_work_entry, sum_hours,
                validate_and_sort_schedule)

########################################
# Tests

time_gap_test_cases = [
    # Normal cases
    {"id": "1day", "start": "0900", "end": "1700", "expected": 8.0},
    {"id": "frac_hours", "start": "0830", "end": "0915", "expected": 0.75},

    # Midnight wraparound cases
    {"id": "cross_midnight", "start": "2300", "end": "0100", "expected": 2.0},
    {"id": "full_day", "start": "0800", "end": "0800", "expected": 0.0},
    {"id": "near_day", "start": "0000", "end": "2359", "expected": 1439/60},

    # Edge cases
    {"id": "zero_length", "start": "1200", "end": "1200", "expected": 0.0},
    {"id": "one_minute", "start": "2359", "end": "0000", "expected": 1/60},
    {"id": "bad_hrs_hi", "start": "2500", "end": "1000", "expected": "error"},
    {"id": "bad_neg_hrs", "start": "-100", "end": "0900", "expected": "error"},
    {"id": "bad_min_hi", "start": "0860", "end": "0900", "expected": "error"},
    {"id": "bad_short_fmt", "start": "900", "end": "1000", "expected": "error"}
]


@pytest.mark.parametrize("case", time_gap_test_cases,
                         ids=[c["id"] for c in time_gap_test_cases])
def test_compute_time_gap(case):
    "Test time gap computation"
    if case.get("expected") == "error":
        with pytest.raises(ValueError):
            compute_time_gap_hours(case["start"], case["end"])
    else:
        result = compute_time_gap_hours(case["start"], case["end"])
        assert result == pytest.approx(case["expected"], abs=1e-9)


parse_test_cases = [
    # Valid cases
    {
        "id": "valid_entry_1",
        "line": "!WORK-GSR 20250506 0900 1100 Victoria in-p: staffing, foo",
        "expected": ("GSR", "20250506", "0900", "1100",
                     "Victoria in-p: staffing, foo"),
        "raises": False
    },
    {
        "id": "valid_entry_2",
        "line": "!WORK-DT 20250506 1400 1500 Sonic weekly",
        "expected": ("DT", "20250506", "1400", "1500", "Sonic weekly"),
        "raises": False
    },
    {
        "id": "entry_with_whitespace",
        "line": "  !WORK-DT 20250506 1400 1500   Sonic weekly  ",
        "expected": ("DT", "20250506", "1400", "1500", "Sonic weekly"),
        "raises": False
    },
    {
        "id": "numeric_description",
        "line": "!WORK-DT 20250506 1400 1500 123# test!",
        "expected": ("DT", "20250506", "1400", "1500", "123# test!"),
        "raises": False
    },
    {
        "id": "other_business",
        "line": "!WORK-XY 20250506 1400 1500 desc",
        "expected": ("XY", "20250506", "1400", "1500", "desc"),
        "raises": False
    },

    # Invalid cases
    {
        "id": "invalid_date_length",
        "line": "!WORK-DT 202505061 1400 1500 desc",
        "expected": None,
        "raises": True
    },
    {
        "id": "invalid_start_time_length",
        "line": "!WORK-GSR 20250506 09000 1100 desc",
        "expected": None,
        "raises": True
    },
    {
        "id": "missing_end_time",
        "line": "!WORK-DT 20250506 1400 150 desc",
        "expected": None,
        "raises": True
    },
    {
        "id": "missing_description",
        "line": "!WORK-GSR 20250506 0900 1100",
        "expected": None,
        "raises": True
    },
    {
        "id": "empty_description",
        "line": "!WORK-GSR 20250507 1234 2359    ",
        "expected": None,
        "raises": True
    }
]


@pytest.mark.parametrize("case", parse_test_cases,
                         ids=[case["id"] for case in parse_test_cases])
def test_parse_work_entry(case):
    "Test cases for parsing"
    if case["raises"]:
        with pytest.raises(ValueError):
            parse_work_entry(case["line"])
    else:
        debug('Testing if parse_work_entry(case["line"])'
              f'({parse_work_entry(case["line"])})'
              ' == case["expected"] '
              f'({case["expected"]})')
        assert parse_work_entry(case["line"]) == case["expected"]


schedule_test_cases = [
    # Valid cases
    {
        "id": "non_overlapping_sequential",
        "input": [
            ("20231005", "0900", "1000", 1.0, "Meeting"),
            ("20231005", "1000", "1100", 1.0, "Work session")
        ],
        "expected": [
            ("20231005", "0900", "1000", 1.0, "Meeting"),
            ("20231005", "1000", "1100", 1.0, "Work session")
        ],
        "raises": False
    },
    {
        "id": "different_dates",
        "input": [
            ("20231006", "0900", "1000", 1.0, "Day 2"),
            ("20231005", "1400", "1500", 1.0, "Day 1")
        ],
        "expected": [
            ("20231005", "1400", "1500", 1.0, "Day 1"),
            ("20231006", "0900", "1000", 1.0, "Day 2")
        ],
        "raises": False
    },
    {
        "id": "valid_wraparound",
        "input": [
            ("20231005", "2300", "0200", 3.0, "Night"),
            ("20231006", "0200", "0400", 2.0, "Morning")
        ],
        "expected": [
            ("20231005", "2300", "0200", 3.0, "Night"),
            ("20231006", "0200", "0400", 2.0, "Morning")
        ],
        "raises": False
    },

    # Invalid cases
    {
        "id": "direct_overlap",
        "input": [
            ("20231005", "0900", "1100", 2.0, "Project"),
            ("20231005", "1000", "1200", 2.0, "Meeting")
        ],
        "raises": True
    },
    {
        "id": "cross_day_overlap",
        "input": [
            ("20231005", "2300", "0200", 3.0, "Night shift"),
            ("20231006", "0100", "0300", 2.0, "Early work")
        ],
        "raises": True
    },
    {
        "id": "contained_overlap",
        "input": [
            ("20231005", "0800", "1700", 9.0, "Workday"),
            ("20231005", "0900", "1600", 7.0, "Task")
        ],
        "raises": True
    },
    {
        "id": "edge_case_same_time",
        "input": [
            ("20231005", "0900", "1000", 1.0, "A"),
            ("20231005", "0900", "1000", 1.0, "B")
        ],
        "raises": True
    }
]


@pytest.mark.parametrize("case", schedule_test_cases,
                         ids=[c["id"] for c in schedule_test_cases])
def test_schedule_validation(case):
    "Test schedule validation"
    if case.get("raises"):
        with pytest.raises(ValueError):
            validate_and_sort_schedule(case["input"])
    else:
        result = validate_and_sort_schedule(case["input"])
        assert result == case["expected"]


sum_hours_test_cases = [
    {
        "id": "empty_list",
        "input": [],
        "expected": 0.0,
        "expected_rows": 1,
        "raises": False
    },
    {
        "id": "single_entry",
        "input": [("20240708", "0800", "0900", "Meeting", 1.5)],
        "expected": 1.5,
        "expected_rows": 2,
        "raises": False
    },
    {
        "id": "multiple_entries",
        "input": [
            ("20240708", "0800", "0900", "Meeting", 1.0),
            ("20240708", "0930", "1030", "Work Session", 1.0),
            ("20240708", "1100", "1130", "Break", 0.5)
        ],
        "expected": 2.5,
        "expected_rows": 4,
        "raises": False
    },
    {
        "id": "fractional_hours",
        "input": [
            ("20240708", "0800", "0830", "Task 1", 0.5),
            ("20240708", "0830", "0845", "Task 2", 0.25),
            ("20240708", "0845", "0900", "Task 3", 0.25)
        ],
        "expected": 1.0,
        "expected_rows": 4,
        "raises": False
    },
    {
        "id": "dataframe_structure",
        "input": [("20240708", "0800", "0900", "Test", 1.5)],
        "expected": 1.5,
        "expected_rows": 2,
        "raises": False
    }
]


@pytest.mark.parametrize("case", sum_hours_test_cases, ids=[c["id"]
                         for c in sum_hours_test_cases])
def test_sum_hours(case):
    "Test the creation of the dataframe"
    if case["raises"]:
        with pytest.raises(ValueError):
            sum_hours(case["input"])
    else:
        result_df = sum_hours(case["input"])

        assert len(result_df) == case["expected_rows"]  # Verify row count
        # Verify total hours in last row
        assert result_df.iloc[-1]['Hours'] == \
               pytest.approx(case["expected"], abs=1e-9)

        # Verify column structure
        expected_columns = ['Date', 'Start', 'End', 'Description', 'Hours']
        assert list(result_df.columns) == expected_columns

        # Special check for empty case
        if case["id"] == "empty_list":
            assert result_df.iloc[0]['Description'] == 'TOTAL'
            assert result_df.iloc[0]['Start'] == ''


date_test_cases = [
    {"id": "valid_date", "input": "20250101", "expected": date(2025, 1, 1)},
    {"id": "invalid_length_short", "input": "202501", "raises": True},
    {"id": "invalid_length_long", "input": "202501010", "raises": True},
    {"id": "non_numeric_chars", "input": "2025a101", "raises": True},
    {"id": "invalid_month", "input": "20251301", "raises": True},
    {"id": "invalid_day", "input": "20250230",  "raises": True}
]


@pytest.mark.parametrize("case", date_test_cases,
                         ids=[c["id"] for c in date_test_cases])
def test_parse_date_string(case):
    """Test date string parsing functionality"""
    if case.get("raises"):
        with pytest.raises(ValueError):
            parse_date_string(case["input"])
    else:
        result = parse_date_string(case["input"])
        assert result == case["expected"]


date_filter_test_cases = [
    {
        "id": "full_range",
        "input_df": pd.DataFrame({
            "Date": ["20230101", "20230102", "20230103", "Total"],
            "Start": ["0900", "1000", "0800", ""],
            "End": ["1700", "1800", "1600", ""],
            "Description": ["A", "B", "C", "Total"],
            "Hours": [8, 8, 8, 24]
        }),
        "start": "20230101",
        "end": "20230103",
        "expected": pd.DataFrame({
            "Date": ["20230101", "20230102", "20230103", "Total"],
            "Start": ["0900", "1000", "0800", ""],
            "End": ["1700", "1800", "1600", ""],
            "Description": ["A", "B", "C", "Total"],
            "Hours": [8, 8, 8, 24]
        })
    },
    {
        "id": "filtered_range",
        "input_df": pd.DataFrame({
            "Date": ["20230101", "20230115", "20230201", "Total"],
            "Start": ["0900", "1000", "0800", ""],
            "End": ["1700", "1800", "1600", ""],
            "Description": ["A", "B", "C", "Total"],
            "Hours": [8, 8, 8, 24]
        }),
        "start": date(2023, 1, 10),
        "end": date(2023, 1, 31),
        "expected": pd.DataFrame({
            "Date": ["20230115", "Total"],
            "Start": ["1000", ""],
            "End": ["1800", ""],
            "Description": ["B", "Total"],
            "Hours": [8, 24]
        })
    },
    {
        "id": "no_matches",
        "input_df": pd.DataFrame({
            "Date": ["20230101", "20230102", "Total"],
            "Start": ["0900", "1000", ""],
            "End": ["1700", "1800", ""],
            "Description": ["A", "B", "Total"],
            "Hours": [8, 8, 16]
        }),
        "start": "20230201",
        "end": "20230228",
        "expected": pd.DataFrame({
            "Date": ["Total"],
            "Start": [""],
            "End": [""],
            "Description": ["Total"],
            "Hours": [16]
        })
    }
]


def debug_dataframe_mismatch(df1, df2, df1_name="DataFrame1",
                             df2_name="DataFrame2"):
    """
    Print detailed debug info for two DataFrames, including values and types.
    """

    print("\n=== Debugging DataFrame Mismatch ===\n")

    # Print column types for both DataFrames
    print(f"{df1_name} Column Types:")
    for col in df1.columns:
        # Check if column has mixed types
        types = df1[col].apply(lambda x: type(x).__name__).unique()
        if len(types) > 1:
            print(f"  {col}: Heterogeneous types {types}")
        else:
            print(f"  {col}: {df1[col].dtype}")

    print(f"\n{df2_name} Column Types:")
    for col in df2.columns:
        types = df2[col].apply(lambda x: type(x).__name__).unique()
        if len(types) > 1:
            print(f"  {col}: Heterogeneous types {types}")
        else:
            print(f"  {col}: {df2[col].dtype}")

    # Print full DataFrame contents
    print(f"\n{df1_name} Contents:")
    print(df1.to_string(index=True))
    print(f"\n{df2_name} Contents:")
    print(df2.to_string(index=True))
    print("\n=== End Debug ===\n")


# Modified test function
@pytest.mark.parametrize("case", date_filter_test_cases,
                         ids=[c["id"] for c in date_filter_test_cases])
def test_date_filtering(case):
    """Test date filtering functionality"""
    # Convert date strings to actual date objects in expected DataFrames
    expected = case["expected"].copy()
    if len(expected) > 1:  # Skip conversion for Total-only cases
        expected.loc[:-1, "Date"] = expected.loc[:-1, "Date"].apply(
            lambda x: parse_date_string(x) if isinstance(x, str) else x
        )

    # Convert string dates to date objects for test input
    input_df = case["input_df"].copy()
    input_df.loc[:-1, "Date"] = input_df.loc[:-1, "Date"].apply(
        lambda x: parse_date_string(x) if isinstance(x, str) else x
    )

    result = filter_work_entries_by_date(input_df, case["start"], case["end"])
    try:
        assert_frame_equal(result.reset_index(drop=True),
                           expected.reset_index(drop=True))
    except AssertionError:
        debug_dataframe_mismatch(result.reset_index(drop=True),
                                 expected.reset_index(drop=True),
                                 df1_name="Result",
                                 df2_name="Expected")
        raise  # Re-raise the exception to fail the test


test_data = [
    ("5", "20240501:20240531", date(2024, 1, 1)),
    ("5/25", "20250501:20250531", None),
    ("5/70", "19700501:19700531", None),
    ("2/24", "20240201:20240229", None),
    ("2/23", "20230201:20230228", None),
    ("2/1900", "19000201:19000228", None),
    ("2/2000", "20000201:20000229", None),
    ("5/2100", "21000501:21000531", None),
    ("0", ValueError, None),  ("13", ValueError, None),
    ("5/", ValueError, None), ("/2024", ValueError, None),
    (" 2 / 24 ", "20240201:20240229", None),
    ("13/2024", ValueError, None),
]


@pytest.mark.parametrize("input_str, expected, base_date", test_data)
def test_expand_month_string(input_str, expected, base_date):
    "Test month string expansion"
    if expected is ValueError:
        with pytest.raises(ValueError):
            expand_month_string(input_str, base_date)
    else:
        result = expand_month_string(input_str, base_date)
        assert result == expected


if __name__ == "__main__":
    import sys

    # Default arguments: verbose mode and current filename
    args = [__file__, "-v"]

    # Allow passing additional arguments via command line
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    # Run pytest with combined arguments
    exit_code = pytest.main(args)
    sys.exit(exit_code)
