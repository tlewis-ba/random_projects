#!/usr/bin/env python3

"Process timekeeping data"

import argparse
import calendar
import os
import re
import sys
from datetime import datetime, timedelta, date
from typing import Generator, Iterable, Tuple, List, Union, Optional
import pandas as pd
import pytest


DEFAULT_INPUT = os.getenv("DT_DEFAULT", "-")


######################################
# Functions

def parse_work_entry(line: str) -> Tuple[str, str, str, str, str]:
    """
    Parses a line of text into its constituent parts: business, date,
    start time, end time, and description.

    Args:
        line (str): The input line to parse, which should follow the format:
                    "!WORK-{DT|GSR} YYYYMMDD HHMM HHMM Description..."

    Returns:
        Tuple[str, str, str, str, str]: A tuple containing the business
                                          code (either 'DT' or 'GSR'),
                                          date (8 digits), start time (4
                                          digits), end time (4 digits),
                                          and the description.

    Raises:
        ValueError: If the line does not conform to the expected format.
    """
    stripped_line = line.strip()
    debug(f"Stripped line: {stripped_line}")
    pattern = r'^\s*!WORK-([A-Z]+)\s+(\d{8})\s+(\d{4})\s+(\d{4})\s+(.*\S)\s*$'
    match = re.fullmatch(pattern, stripped_line)
    if not match:
        raise ValueError(f"Invalid format for line: {line}")
    debug(f"Got match: {match.groups()}")
    return match.groups()


def compute_time_gap_hours(start: str, end: str) -> float:
    """
    Calculate fractional hours between two military time stamps with
    validation.

    Args:
        start: Start time in "HHMM" format (00-23 hours, 00-59 minutes)
        end: End time in "HHMM" format

    Returns:
        float: Duration in hours (0.0-24.0)

    Raises:
        ValueError: For invalid time formats or values
    """
    def validate_time(time_str: str) -> Tuple[int, int]:
        if len(time_str) != 4 or not time_str.isdigit():
            raise ValueError(f"Invalid time format: {time_str}")

        hours = int(time_str[:2])
        minutes = int(time_str[2:])

        if not 0 <= hours <= 23:
            raise ValueError(f"Invalid hours: {hours} in {time_str}")
        if not 0 <= minutes <= 59:
            raise ValueError(f"Invalid minutes: {minutes} in {time_str}")

        return hours, minutes

    # Validate both times
    start_h, start_m = validate_time(start)
    end_h, end_m = validate_time(end)

    # Conversion and calculation (same as before)
    start_total = start_h * 60 + start_m
    end_total = end_h * 60 + end_m

    delta = end_total - start_total \
        if end_total >= start_total \
        else (end_total + 1440) - start_total
    return delta / 60.0


def validate_and_sort_schedule(
    entries: List[Tuple[str, str, str, float, str]]
) -> List[Tuple[str, str, str, float, str]]:
    """
    Validates and sorts schedule entries while checking for time overlaps.
    Preserves all original entry data exactly, only changing the order.

    Args:
        entries: List of entries in (date, start, end, gap, desc) format

    Returns:
        Sorted list of original entries in chronological order

    Raises:
        ValueError: If time overlaps are detected
    """
    parsed = []
    for original_entry in entries:
        debug(f"Processing entry: {original_entry}")
        xdate, start, end, _, _ = original_entry  # Unpack fully

        # Parse times (validation happens here)
        start_dt = datetime.strptime(f"{xdate}{start}", "%Y%m%d%H%M")
        end_dt = datetime.strptime(f"{xdate}{end}", "%Y%m%d%H%M")

        # Handle overnight spans
        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        # Store original entry with parsed times
        parsed.append((start_dt, end_dt, original_entry))

    # Sort by parsed datetime values
    sorted_entries = sorted(parsed, key=lambda x: x[0])

    # Check for overlaps using parsed times
    prev_end = None
    for start_dt, end_dt, original_entry in sorted_entries:
        if prev_end and start_dt < prev_end:
            e = "Overlap detected between entries:" \
                f"start_dt {start_dt} < prev_end {prev_end}\n" \
                f"(Original entry: {original_entry})"
            raise ValueError(e)

        prev_end = max(prev_end, end_dt) if prev_end else end_dt

    # Return original entries in sorted order
    return [original_entry for (_, _, original_entry) in sorted_entries]


def create_hours_df(data: List[Tuple[str, str, str, str, float]]) -> \
        pd.DataFrame:
    """
    Create a DataFrame from validated schedule data.

    Args:
        data: List of schedule entries where each entry is a tuple containing:
            - date (YYYYMMDD)
            - start time (HHMM)
            - end time (HHMM)
            - description
            - hours (float)

    Returns:
        pandas.DataFrame: DataFrame with columns ['Date', 'Start', 'End',
            'Description', 'Hours']
    """
    columns = ['Date', 'Start', 'End', 'Description', 'Hours']
    return pd.DataFrame(data, columns=columns)


def add_total_hours_row(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a 'TOTAL' row with the sum of hours to the DataFrame.

    Args:
        df: DataFrame containing time entries with 'Hours' column

    Returns:
        pandas.DataFrame: Original DataFrame with additional total row
    """
    total_row = pd.DataFrame(
        [['', '', '', 'TOTAL', df['Hours'].sum()]],
        columns=df.columns
    )
    return pd.concat([df, total_row], ignore_index=True)


def sum_hours(data: List[Tuple[str, str, str, str, float]]) -> pd.DataFrame:
    "Legacy function; now decomposed"
    return add_total_hours_row(create_hours_df(data))


def sum_hours_to_markdown(df: pd.DataFrame) -> str:
    """
    Convert a hours-summary DataFrame to a markdown table with total row.

    Handles both the itemized entries and the total row correctly.

    Args:
        df: DataFrame from sum_hours() with columns:
            ['Date', 'Start', 'End', 'Description', 'Hours']

    Returns:
        str: Markdown table with headers, alignment, and total row
    """
    # Create copy to avoid modifying original
    md_df = df.copy()

    # Format numbers to 3 decimal places
    md_df['Hours'] = md_df['Hours'].apply(
            lambda x: f"{x:7.3f}".replace(" ", '\u00a0')
                      if isinstance(x, float) else f"NONFLOAT {x}")

    # Generate markdown table
    markdown = md_df.to_markdown(index=False, tablefmt="github",
                                 disable_numparse=True)
    return markdown


######################################
# Utilities

_debug = int(os.getenv("DEBUG", "0"))


def debug(msg, level=1):
    "Optionally emit debug messages.  Use priority `-1` to force the output."
    if level <= _debug:
        for line in msg.splitlines():
            print(f"# DEBUG[{level}]: {line}", file=sys.stderr)


def dump_df(df):
    "Dump dataframe"
    with pd.option_context(
        'display.max_columns', None,          # Show all columns
        'display.max_colwidth', None,         # Full column content
        'display.expand_frame_repr', False,   # No line wrapping
        'display.max_rows', None              # Show all rows
    ):
        return df.to_string(index=False)


def filter_work_entries_by_date(
    df: pd.DataFrame,
    start_date: Union[str, date],
    end_date: Union[str, date]
) -> pd.DataFrame:
    """
    Filter work entries DataFrame by date range while preserving the final
    'Total' row.
    """
    if isinstance(start_date, str):
        start_date = parse_date_string(start_date)
    if isinstance(end_date, str):
        end_date = parse_date_string(end_date)

    keep_indices = []
    # This loop correctly identifies the indices of rows to keep,
    # handling both date objects and date strings in the input.
    for index, row_date in df['Date'].items():
        if row_date == 'Total':
            keep_indices.append(index)
            continue

        try:
            # Use the value if it's already a date, otherwise parse it.
            current_date = row_date if isinstance(row_date, date) \
                                    else parse_date_string(row_date)
            if start_date <= current_date <= end_date:
                keep_indices.append(index)
        except (ValueError, TypeError):
            # Ignore rows with invalid date formats or non-date strings
            continue

    # Create a new DataFrame from the selected rows
    result_df = df.loc[keep_indices].copy()

    # The test expects string dates, not date objects.
    # Convert any date objects in the final DataFrame back to 'YYYYMMDD'
    # strings.
    result_df['Date'] = result_df['Date'].apply(
        lambda x: x.strftime('%Y%m%d') if isinstance(x, date) else x
    )

    return result_df


def parse_date_string(date_str: str) -> date:
    """
    Parse a date string in YYYYMMDD format into a datetime.date object.

    Args:
        date_str: String representing a date in 'YYYYMMDD' format.

    Returns:
        datetime.date object corresponding to the input string.

    Raises:
        ValueError: If input is not 8 characters, contains non-digit
                    characters, or does not represent a valid date.
    """
    # Validate string length and digit-only format
    if len(date_str) != 8:
        raise ValueError("Date string must be exactly 8 characters long")
    if not date_str.isdigit():
        raise ValueError("Date string must contain only numeric characters")

    # Attempt to parse the date components
    try:
        return datetime.strptime(date_str, "%Y%m%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date components in {date_str}") from e


def expand_month_string(s: str, base_date: Optional[date] = None) -> str:
    """
    Parse a month or month/year string and return a date range covering
    that month.

    The input string can be in two forms:
    - "5"       (month only, uses current year from base_date)
    - "5/25"    (month/year where year can be 2 or 4 digits)

    For 2-digit years:
    - 00-69 → 2000-2069
    - 70-99 → 1970-1999

    Args:
        s: Input string in "month" or "month/year" format
        base_date: Reference date for determining current year
                   (defaults to today)

    Returns:
        String in "YYYYMMDD:YYYYMMDD" format representing the first and
        last day of the month

    Raises:
        ValueError: For invalid formats, empty components, or month
        outside 1-12 range

    Examples:
        "5"         → "20250501:20250531" (using current year)
        "5/25"      → "20250501:20250531"
        "2/24"      → "20240201:20240229" (leap year)
        " 2 / 24 "  → "20240201:20240229" (whitespace tolerant)
    """
    if base_date is None:
        base_date = date.today()
    current_year = base_date.year

    parts = s.split('/')
    if len(parts) == 1:
        month_str = parts[0].strip()
        if not month_str:
            raise ValueError("Invalid month: empty string")
        month = int(month_str)
        year = current_year
    elif len(parts) == 2:
        month_str = parts[0].strip()
        year_str = parts[1].strip()
        if not month_str or not year_str:
            raise ValueError(f"Invalid input string: {s}")
        month = int(month_str)
        year_val = int(year_str)
        if year_val < 100:
            year = 2000 + year_val if year_val <= 69 else 1900 + year_val
        else:
            year = year_val
    else:
        raise ValueError(f"Invalid input string: {s}")

    if month < 1 or month > 12:
        raise ValueError(f"Month must be between 1 and 12, got {month}")

    first_day = date(year, month, 1)
    _, num_days = calendar.monthrange(year, month)
    last_day = date(year, month, num_days)

    return f"{first_day:%Y%m%d}:{last_day:%Y%m%d}"


def process_lines(
        f: Iterable[str]
        ) -> Generator[Tuple[str, str, str, str, str], None, None]:
    """
    Process lines from a file-like object, yielding parsed work entries.

    Args:
        f: An iterable of strings (typically a file object) containing
           work entries

    Yields:
        Tuples containing:
        - Business code (DT/GSR)
        - Date (YYYYMMDD)
        - Start time (HHMM)
        - End time (HHMM)
        - Description

    Raises:
        ValueError: If any line fails parsing via parse_work_entry
    """
    for line in f:
        # Only process non-empty lines starting with !WORK
        stripped_line = line.strip()
        if not stripped_line.startswith('!WORK'):
            continue

        business, xdate, start, end, desc = parse_work_entry(line)
        debug(f"[{business}] {xdate} {start}-{end}: {desc}")
        yield business, xdate, start, end, desc


def make_final_markdown(mds, daterange=None):
    "build unified markdown report"
    if daterange:
        yield f"Data covering range {' to '.join(daterange.split(':'))}:\n"
    for client in sorted(mds.keys()):
        yield f"# {client}\n\n" + mds[client] + "\n\n"


def process_data(clients, daterange=None):
    "Take monolithic data, separate by client, validate, generate markdown"
    mds = {}
    for client in sorted(clients.keys()):
        debug(f"Data for client {client}: {clients[client]}")
        # validate data
        validated_client_data = validate_and_sort_schedule(clients[client])
        debug(f"Validated data for {client}[{len(validated_client_data)}]:")
        debug(f"    {validated_client_data}")

        # make dataframe
        df = create_hours_df(validated_client_data)
        # process daterange
        if daterange:
            dr_start, dr_end = daterange.split(":")
            df = filter_work_entries_by_date(df, dr_start, dr_end)
            debug(f"Dataframe for {client} post-filtering: {dump_df(df)}")
        # sum hours
        df = add_total_hours_row(df)
        debug(f"Dataframe for {client} with total hours: {dump_df(df)}")
        # convert to markdown
        md = sum_hours_to_markdown(df)
        debug(f"Markdown for {client}:\n{md}")
        mds[client] = md
    return mds


def process_file(f, daterange=None):
    "High-level processing of an input file"
    clients = {}
    debug(f"Starting processing from {f}, "
          f"clients is {clients}")

    # process file
    for (business, xdate, start, end, desc) in process_lines(f):
        gap = compute_time_gap_hours(start, end)
        debug(f"Got tuple: (business={business}, date={xdate}, "
              f"start={start}, end={end}, desc={desc}, "
              f"gap={gap:.3f})")
        if business not in clients:
            clients[business] = []
        debug(f"adding to clients[{business}]: [["
              f"{(xdate, start, end, desc, gap)}]]")
        clients[business] += [(xdate, start, end, desc, gap)]

    mds = process_data(clients, daterange)
    yield from make_final_markdown(mds, daterange)
    debug(f"Ending processing from {f}")


def make_parser():
    "Makes and returns an ArgumentParser"
    parser = argparse.ArgumentParser(
        description="Parse WORK entries from lines starting with '!WORK'",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # You can take the boy out of perl,
    # but you can't take the perl out of the boy.
    _ = [parser.add_argument(*f, **p) for f, p in [
        (['-t', '--test'], {'action': 'store_true', 'help': 'Run unit tests'}),
        (['input_source'], {
            'nargs': '?',
            'type': argparse.FileType('r'),
            'default': DEFAULT_INPUT,
            'help': "Input ('-' for stdin, default: " +
                    DEFAULT_INPUT + ")"
        }),
        (['-d', '--debug'], {'nargs': '?',
                             'default': None, 'const': "1",
                             'help': 'Debug level (integer)'}),
        (['-r', '--range'], {'default': None,
                             'help': "Specify range: '20250101:20250131'"}),
        (['-m', '--month'], {'const': str(datetime.now().month), 'nargs': '?',
                             'help': "Specify range: '5' or `5/25`"})
    ]]
    return parser


########################################
# Main

def main():
    "Main program"

    args = make_parser().parse_args()

    if args.debug:
        global _debug  # pylint: disable=global-statement # So dumb.
        _debug = int(args.debug)

    if args.test:  # Run pytest and exit with test status
        # Get the directory of the current file and construct test file path
        basedir = os.path.dirname(os.path.abspath(__file__))
        test_path = os.path.join(basedir, "tk_test.py")
        return pytest.main([test_path, "-v"])

    drange = args.range

    # allow single-day ranges
    if drange and drange.isdecimal() and len(drange) == 8:
        drange = f"{drange}:{drange}"

    if args.month:
        drange = expand_month_string(args.month)

    try:
        # No changes needed here, as args.input_source is an open file handle
        [print(x) for x in process_file(args.input_source, drange)]
    except FileNotFoundError:
        print(f"Error: Default file '{args.input_source.name}' not found.",
              file=sys.stderr)
        return 1
    except BrokenPipeError:  # Handle pipe closure (e.g., when piping to head)
        sys.stderr.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
