import os
import re
import numpy as np
import pandas as pd
import html
import json
import math
import random
import xml.etree.ElementTree as ET

def na_omit_list(obj):
    """
    Remove NA entries from a list or dict.

    Entries whose values are *all*
    missing are dropped, everything else is kept untouched.

    :param obj: A list, tuple or dict
    :return: A cleaned object of the same kind
    """
    def _all_na(x):
        if x is None:
            return True
        if isinstance(x, float) and math.isnan(x):
            return True
        if x is pd.NA or x is pd.NaT:
            return True
        if isinstance(x, (pd.Series, pd.Index, np.ndarray)):
            return len(x) > 0 and pd.isna(x).all()
        if isinstance(x, pd.DataFrame):
            return x.empty or x.isna().all().all()
        if isinstance(x, (list, tuple, set)):
            return len(x) > 0 and all(_all_na(v) for v in x)
        return False

    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if not _all_na(v)}
    return type(obj)(v for v in obj if not _all_na(v))


def confirm_action():
    """
    Ask the user to confirm script execution.

    :return: True if execution should proceed
    :rtype: bool
    :raises Exception: if the user cancels the action
    """
    silent = os.getenv("epi_silent")
    if silent == "TRUE":
        return True

    user_input = input("Are you sure you want to proceed? (y/n)  ")
    if user_input != "y":
        raise Exception("Canceled")


def is_local_server(server):
    """
    Check whether the URL is on a local server.

    :param server: The server URL
    :type server: str
    :return: True if the server is localhost or 127.0.0.1, otherwise False
    :rtype: bool
    """
    return (
        server.startswith("https://127.0.0.1") or
        server.startswith("http://127.0.0.1") or
        server.startswith("https://localhost") or
        server.startswith("http://localhost")
    )


_TAG_RE = re.compile(r"<[^>]*>")


def unescape_html(value, strip_tags=True):
    """
    Remove HTML entities

    Parse the value as HTML and
    return its text content, i.e. entities are resolved and markup is removed.

    :param value: A string or None/NaN
    :param strip_tags: Whether to drop markup as xml2::xml_text() does
    :return: The unescaped string, or the input if it is missing
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return value
    if value is pd.NA:
        return value
    text = str(value)
    if strip_tags:
        text = _TAG_RE.sub("", text)
    return html.unescape(text)


def unescape_cols(df, cols, strip_tags=False):
    """
    Apply unescape_html() to selected columns of a DataFrame.

    :param df: A pandas DataFrame
    :param cols: Column names; missing ones are ignored
    :param strip_tags: Whether to remove markup as well
    :return: DataFrame with the columns unescaped
    """
    df = df.copy()
    for col in cols:
        if col not in df.columns:
            continue
        df[col] = df[col].map(
            lambda v: unescape_html(v, strip_tags=strip_tags)
            if isinstance(v, str) else v
        )
    return df



def drop_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove columns that contain only missing values."""

    #return df.dropna(axis=1, how='all')

    if df.empty:
        return df
    return df.loc[:, df.notna().any()]

def add_missing_columns(df, cols, default=None):
    """
    Add columns with a default value if they are missing from the DataFrame.

    :param df: A pandas DataFrame
    :param cols: A column name or list of column names
    :param default: Default value for added columns
    :return: DataFrame with the missing columns added
    """
    if isinstance(cols, str):
        cols = [cols]
    df = df.copy()
    for col in cols:
        if col not in df.columns:
            df[col] = default
    return df


def move_cols_to_front(df, cols):
    """
    Shift selected columns to the front of a DataFrame.

    :param df: A pandas DataFrame
    :param cols: A list of column names to move to the front
    :return: A DataFrame starting with the selected columns (if present)
    """
    existing = [col for col in cols if col in df.columns]
    remaining = [col for col in df.columns if col not in existing]
    return df[existing + remaining]


def move_cols_to_end(df, cols):
    """
    Shift selected columns to the end of a DataFrame.

    :param df: A pandas DataFrame
    :param cols: A list of column names to move to the end
    :return: A DataFrame ending with the selected columns (if present)
    """
    existing = [col for col in cols if col in df.columns]
    remaining = [col for col in df.columns if col not in existing]
    return df[remaining + existing]

def parse_json(data):
    """
    Parse a column of JSON strings into a DataFrame.

    Empty arrays and missing values are treated as empty objects.

    :param data: An iterable or Series of JSON strings
    :return: A DataFrame with one row per input value
    """
    series = data if isinstance(data, pd.Series) else pd.Series(list(data))
    series = series.astype("object")
    series = series.where(series.notna(), "{}")
    series = series.replace({"[]": "{}", "": "{}"})

    records = []
    for value in series:
        try:
            parsed = json.loads(value) if isinstance(value, str) else value
        except (TypeError, ValueError):
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {"value": parsed}
        records.append(parsed)

    return pd.json_normalize(records)

def num2abc(number, base=26):
    """
    Convert a number to letters, e.g. 3 becomes "c", 27 becomes "aa".

    :param number: A positive integer
    :param base: Number of letters to use
    :return: The letter representation
    """
    number = int(number)
    if number < 1:
        raise ValueError("number must be >= 1")

    letters = [chr(ord("a") + i) for i in range(base)]

    n, offset, block = 1, 0, base
    while number > offset + block:
        offset += block
        block *= base
        n += 1

    digits = encode(number - offset - 1, [base] * n)
    return "".join(letters[d] for d in digits)


def abc2num(s, base=26):
    """
    Convert letters to a number, e.g. "c" becomes 3, "aa" becomes 27.

    :param s: The string to convert
    :param base: Number of letters to use
    :return: The resulting integer
    """
    s = str(s).lower()
    digits = [ord(ch) - ord("a") for ch in s]
    if any(d < 0 or d >= base for d in digits):
        raise ValueError(f"Invalid letters in {s!r}")

    n = len(digits)
    offset = sum(base ** k for k in range(1, n))
    return decode(digits, [base] * n) + offset + 1

def encode(number, base):
    """
    Convert a number using a radix vector (APL encode / representation "T").

    :param number: An integer or a list of integers
    :param base: An integer radix or a list of radices
    :return: A list of digits (list of lists for multiple numbers)
    """
    bases = [base] if isinstance(base, (int, float)) else list(base)
    scalar = not hasattr(number, "__iter__")
    numbers = [number] if scalar else list(number)

    result = []
    for value in numbers:
        value = int(value)
        digits = [0] * len(bases)
        for i in range(len(bases) - 1, -1, -1):
            if bases[i] > 0:
                digits[i] = value % bases[i]
                value = value // bases[i]
            else:
                digits[i] = value
                value = 0
        result.append(digits)

    return result[0] if scalar else result


def decode(b, base):
    """
    Convert digits using a radix vector (APL decode / base "_|_").

    :param b: A list of digits
    :param base: An integer radix or a list of radices
    :return: The resulting integer
    """
    digits = [int(x) for x in b]
    bases = [base] * len(digits) if isinstance(base, (int, float)) else list(base)

    number = 0
    weight = 1
    for i in range(len(digits) - 1, -1, -1):
        number += digits[i] * weight
        weight *= bases[i]
    return number


def pseudonyms(n, seed=None):
    """
    Create distinct pseudonyms.

    :param n: Number of pseudonyms
    :param seed: Optional random seed
    :return: A list of distinct pseudonyms
    """
    rng = random.Random(seed)
    consonants = list("bcdfghjklmnpqrstvwxz")
    vowels = list("aeiou")

    candidates = []
    seen = set()
    iterations = 0

    while len(candidates) < n:
        if iterations > 100:
            raise Exception("Could not create sufficient values in 100 iterations.")

        for _ in range(n - len(candidates)):
            word = (rng.choice(consonants).upper() + rng.choice(vowels)
                    + rng.choice(consonants) + rng.choice(vowels)
                    + rng.choice(consonants) + rng.choice(vowels))
            if word not in seen:
                seen.add(word)
                candidates.append(word)

        iterations += 1

    return candidates

def bind_rows_char(dataframes):
    """
    Bind rows of DataFrames even if column types differ.

    Columns whose dtype differs between the frames are converted to string
    before concatenating.

    :param dataframes: An iterable of DataFrames
    :return: A single concatenated DataFrame
    """
    frames = [df for df in dataframes if df is not None and not df.empty]
    if not frames:
        return pd.DataFrame()

    col_names = list(dict.fromkeys(c for df in frames for c in df.columns))

    to_character = set()
    for col in col_names:
        kinds = {df[col].dtype.kind for df in frames if col in df.columns}
        if len(kinds) > 1:
            to_character.add(col)

    if to_character:
        frames = [
            df.assign(**{c: df[c].astype("string")
                         for c in to_character if c in df.columns})
            for df in frames
        ]

    frames = [df.reindex(columns=col_names) for df in frames]
    return pd.concat(frames, ignore_index=True, sort=False)

def merge_lists(items):
    """
    Merge dict elements by their name.

    Values sharing a key are collected into a list, in the order of the input.

    :param items: An iterable of dicts
    :return: A merged dict
    """
    merged = {}
    for entry in items:
        if not entry:
            continue
        for key, value in entry.items():
            merged.setdefault(key, []).append(value)
    return {k: (v[0] if len(v) == 1 else v) for k, v in merged.items()}


def merge_vectors(values, default):
    """
    Merge two named vectors (dicts).

    :param values: A dict whose entries take precedence
    :param default: A dict with fallback entries
    :return: The defaults updated with all entries from values
    """
    merged = dict(default or {})
    merged.update(values or {})
    return merged


def default_values(df, colname, default=None):
    """
    Set a default value for a column if it is missing.

    :param df: A pandas DataFrame
    :param colname: A column name
    :param default: Value used when the column has to be created
    :return: DataFrame containing the column
    """
    if colname in df.columns:
        return df
    df = df.copy()
    df[colname] = default
    return df

def get_extension(path):
    filename = os.path.basename(path)

    # Check if filename has a dot and something after it
    if "." in filename:
        ext_match = re.sub(r".*\.(.*)$", r"\1", filename)

        # If the dot is at the start (hidden files like .bashrc), treat as no extension
        if filename.startswith(".") and not re.search(r"\..+\.", filename):
            return ""
        else:
            return ext_match
    else:
        return ""

def join_path(filename, filepath=None):
    """
    Join folder and filename.

    :param filename: File name
    :param filepath: Target folder or None
    :return: The joined path
    """
    if filepath is None or filepath == "":
        return filename
    return os.path.join(filepath, filename)



def annotate_offsets(xml):
    """
    Inject character offsets into id-bearing XML elements.

    Walks the XML tree once in document order, accumulating a running character
    offset over all text nodes, and stamps ``data-start`` and ``data-end``
    attributes onto every element that carries an ``id`` attribute. Offsets are
    1-based and inclusive and refer to positions in the plain (tag-stripped)
    text.

    The input is wrapped in a synthetic ``<root>`` element so that fragments
    with multiple top-level nodes can be parsed.

    :param xml: A string containing XML text, possibly a fragment
    :return: The annotated root Element
    """
    root = ET.fromstring(f"<root>{xml}</root>")
    offset = 0

    def walk(node):
        nonlocal offset
        start = offset + 1

        if node.text:
            offset += len(node.text)
        for child in node:
            walk(child)
            if child.tail:
                offset += len(child.tail)

        if node.get("id") is not None:
            node.set("data-start", str(start))
            node.set("data-end", str(offset))

    walk(root)
    return root


def covered_length(start, end):
    """
    Total length covered by a set of integer intervals.

    Merges overlapping/adjacent ``[start, end]`` ranges and sums their widths,
    so overlapping annotations are counted once. Ranges are 1-based inclusive.

    :param start: Iterable of range starts
    :param end: Iterable of range ends
    :return: The number of distinct positions covered
    """
    spans = sorted(zip([int(s) for s in start], [int(e) for e in end]))
    if not spans:
        return 0

    total = 0
    cur_lo, cur_hi = spans[0]
    for lo, hi in spans[1:]:
        if lo <= cur_hi + 1:                  # overlapping or adjacent
            cur_hi = max(cur_hi, hi)
        else:
            total += cur_hi - cur_lo + 1
            cur_lo, cur_hi = lo, hi
    return total + (cur_hi - cur_lo + 1)

def str_as_nullable(series: pd.Series) -> pd.Series:
    """Convert a Series to str, turning 'nan'/'None' back to pd.NA."""
    series = series.astype(str)
    series[series.isin({"nan", "None", "<NA>"})] = pd.NA
    return series

def as_str_series(value) -> tuple[pd.Series, bool]:
    """Coerce scalars / lists / arrays / Series to a string Series.

    :return: (series, was_scalar)
    """
    if isinstance(value, pd.Series):
        return value.astype("string"), False
    if isinstance(value, pd.Index):
        return pd.Series(value).astype("string"), False
    if value is None or isinstance(value, str) or not hasattr(value, "__iter__"):
        return pd.Series([value], dtype="string"), True
    return pd.Series(list(value), dtype="string"), False


def is_list(value):
    """
    Check whether a value is a list with more than one element.

    :param value: A string or iterable with names
    :return: True if the value contains more than one name
    """
    return not isinstance(value, str) and hasattr(value, "__len__") and len(value) > 1


def as_list(value):
    """
    Return a plain list from any iterable.

    :param value: A string, list, tuple, set, or pandas Series
    :return: A list
    """
    try:
        return value.tolist()  # pandas Series
    except AttributeError:
        return list(value)


def as_string(s: pd.Series) -> pd.Series:
    """
    Normalise a join key so that 12, 12.0 and '12' match.

    :param s: A pandas Series
    :return: A string Series
    """
    if pd.api.types.is_float_dtype(s) or pd.api.types.is_integer_dtype(s):
        try:
            return s.astype("Int64").astype("string")
        except (TypeError, ValueError):
            pass
    return s.astype("string")

def str_detect(value, pattern: str):
    """Detect whether a string contains a regex pattern."""
    s, scalar = as_str_series(value)
    res = s.str.fullmatch(pattern).fillna(False).astype(bool)
    return bool(res.iloc[0]) if scalar else res

def dedup_columns(df: pd.DataFrame) -> pd.DataFrame:
    """bind_rows()/concat() need unique column labels."""
    return df.loc[:, ~df.columns.duplicated()]

def dedup_rows(frame: pd.DataFrame, key: str,
                       marker: str = "modified") -> pd.DataFrame:
    """Reduce *frame* to one row per *key*.

    RAM frames contain two kinds of rows for the same entity: sparse rows that
    only carry the link (foreign keys) and the full record. Only the full
    record has a ``modified`` timestamp, so rows with a non-null *marker* win.
    If several full rows exist, the most recently modified one is kept.
    Without a *marker* column we fall back to the row with the most values.
    """
    if frame.empty or key not in frame.columns:
        return frame
    if not frame[key].duplicated().any():
        return frame

    work = frame.reset_index(drop=True)
    order = pd.Series(range(len(work)), index=work.index)

    if marker and marker in work.columns:
        mark = work[marker]
        if not pd.api.types.is_datetime64_any_dtype(mark):
            parsed = pd.to_datetime(mark, errors="coerce", utc=True)
            if parsed.notna().any():
                mark = parsed
        tmp = work.assign(_has=mark.notna().astype(int), _mark=mark, _ord=order)
        tmp = tmp.sort_values(
            ["_has", "_mark", "_ord"],
            ascending=[False, False, True],
            kind="stable", na_position="last",
        )
    else:
        tmp = work.assign(_filled=work.notna().sum(axis=1), _ord=order)
        tmp = tmp.sort_values(["_filled", "_ord"],
                              ascending=[False, True], kind="stable")

    tmp = tmp.drop_duplicates(subset=key, keep="first").sort_values("_ord")
    return tmp[list(frame.columns)].reset_index(drop=True)

def bind_rows(frames) -> pd.DataFrame:
    """Concat data frames with union of columns and order of first appearance."""
    frames = [f for f in frames
              if f is not None and f.shape[0] > 0 and f.shape[1] > 0]
    if not frames:
        return pd.DataFrame()
    cols = list(dict.fromkeys(c for f in frames for c in f.columns))
    frames = [dedup_columns(f).reindex(columns=cols) for f in frames]
    return pd.concat(frames, ignore_index=True, sort=False)
