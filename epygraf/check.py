from epygraf import base


def has_column(data, col: str, msg: str = None) -> bool:
    """
    Check whether a column exists and raise an error if not.

    Mirrors check_has_column() from checks.R.

    :param data: A pandas DataFrame
    :param col: Column name
    :param msg: Optional custom error message
    :return: True if column exists
    """
    if not isinstance(col, str) or col == "":
        raise ValueError(msg or "Did you miss to say which column to use?")

    if col not in data.columns:
        raise ValueError(msg or f"The column {col} does not exist, check your parameters.")

    return True


def is_id(value, msg: str = None) -> bool:
    """
    Check whether a value is a valid Epigraf ID and raise an error if not.

    Mirrors check_is_id() from checks.R.

    :param value: A character value (e.g. "articles-123")
    :param msg: Optional custom error message
    :return: True if the ID is valid
    """
    check = base.is_id(value)
    if not check:
        raise ValueError(msg or f"The value {value} is not a valid Epigraf ID.")
    return True


def is_db(value: str, msg: str = None) -> bool:
    """
    Check whether a value is a valid database name and raise an error if not.

    Mirrors check_is_db() from checks.R.

    :param value: A database name string
    :param msg: Optional custom error message
    :return: True if value is a string
    """
    if not isinstance(value, str):
        raise ValueError(msg or f"The value {value} is not a valid Epigraf database name.")
    return True
