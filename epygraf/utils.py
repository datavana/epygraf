import os
import re
import pandas as pd


def drop_empty_columns(df):
    return df.dropna(axis=1, how='all')

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

def move_cols_to_front(df, cols):
    """
    Shift selected columns to the front of a DataFrame.

    Mirrors move_cols_to_front() from utils.R.

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

    Mirrors move_cols_to_end() from utils.R.

    :param df: A pandas DataFrame
    :param cols: A list of column names to move to the end
    :return: A DataFrame ending with the selected columns (if present)
    """
    existing = [col for col in cols if col in df.columns]
    remaining = [col for col in df.columns if col not in existing]
    return df[remaining + existing]


def is_multi_db(db):
    """
    Check whether db represents multiple databases.

    :param db: A string or iterable of database names
    :return: True if db contains more than one name
    """
    return not isinstance(db, str) and hasattr(db, "__len__") and len(db) > 1


def iter_dbs(db):
    """
    Return a plain list of database names from any iterable.

    :param db: A string, list, tuple, set, or pandas Series of database names
    :return: A list of database name strings
    """
    try:
        return db.tolist()   # pandas Series
    except AttributeError:
        return list(db)


def add_missing_columns(df, cols, default=None):
    """
    Add columns with a default value if they are missing from the DataFrame.

    Mirrors add_missing_columns() from utils.R.

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
