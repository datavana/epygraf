import os
import re
import pandas as pd
import pymysql
from pymysql import cursors
from numbers import Number
from epygraf import check, utils


def setup(host="localhost", port=3306, username="root", password="root", database=""):
    """
    Set up environment variables for connecting to a database.

    :param host: (str) The hostname or IP address of the database server.
                  Default is 'localhost'.
    :param port: (int) The port number for the database server. Default is 3306.
    :param username: (str) The username for connecting to the database.
                      Default is 'root'.
    :param password: (str) The password for connecting to the database.
                      Default is 'root'.
    :param database: (str) The name of the database to connect to.
                     Default is an empty string.
    :return: None
    """

    settings = {
        "epi_host": host,
        "epi_port": str(port),
        "epi_username": username,
        "epi_password": password,
        "epi_dbname": database
    }

    for key, value in settings.items():
        os.environ[key] = str(value)

# Initial setup using defaults
setup()

def connect(db=None):
    """
    Connect to a database using the provided or environment-based parameters.

    :param db: (str or None) The name of the database to connect to. If None,
               uses the database name from environment variables.
    :return: pymysql.connections.Connection
        A connection to the MySQL database.
    """
    if db is None:
        db = os.environ.get("epi_dbname")

    con = pymysql.connect(
        host=os.environ.get("epi_host"),
        port=int(os.environ.get("epi_port")),
        user=os.environ.get("epi_username"),
        password=os.environ.get("epi_password"),
        database=db
    )

    return con


# ---------------------------------------------------------------------------
# Internal SQL helpers
# ---------------------------------------------------------------------------

def _is_na(value):
    """Return True when value is None or a non-string NA."""
    return value is None or (not isinstance(value, str) and pd.isna(value))


def _sql_literal(value):
    """Convert a Python value to a safe SQL literal string."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, Number):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _cond_to_filter(cond):
    """
    Convert a dict of {field: value(s)} conditions to a list of SQL WHERE clauses.

    :param cond: None, a str, a list of str, or a dict of field→value mappings
    :return: None or a list of SQL condition strings
    """
    if cond is None:
        return None
    if isinstance(cond, str):
        return [cond]
    if isinstance(cond, (list, tuple)):
        return list(cond)
    if not isinstance(cond, dict):
        raise TypeError("cond must be a dict, list, str, or None")

    clauses = []
    for field, raw in cond.items():
        if _is_na(raw):
            continue
        if isinstance(raw, (list, tuple, set)):
            values = [v for v in raw if not _is_na(v)]
        elif hasattr(raw, "tolist"):
            values = [v for v in raw.tolist() if not _is_na(v)]
        else:
            values = [raw]
        if not values:
            continue
        joined = ", ".join(_sql_literal(v) for v in values)
        clauses.append(f"{field} IN ({joined})")
    return clauses


def table(table, cond=None, db=None, deleted=False, compact=False):
    """
    Retrieve data from a table.

    :param table: (str) The table name.
    :param cond: (dict, list, str, or None) Filter conditions.
                 Pass a dict of {field: value(s)} for named conditions (like R's named list),
                 a list of raw SQL condition strings, or a single SQL condition string.
    :param db: (pymysql.connections.Connection or str) The database connection object or name.
               Provide a list of database names to get and row-bind data from multiple databases.
               In that case compact is automatically set to True.
               If None, uses the database name from the settings.
    :param deleted: (bool) Include deleted records. Default is False.
    :param compact: (bool) Whether to add `table` and `database` columns and normalise
                   the type column to `type`. Mirrors the compact parameter in db_table() from db.R.
    :return: pandas.DataFrame
    """
    # If db is a list of databases, iterate and bind (mirrors R db_table multi-db)
    if not isinstance(db, pymysql.connections.Connection) and not isinstance(db, str) and \
            db is not None and hasattr(db, "__len__") and len(db) > 1:
        frames = []
        for single_db in (db.tolist() if hasattr(db, "tolist") else list(db)):
            frames.append(table(table, cond=cond, db=single_db, deleted=deleted, compact=True))
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # Get database connection
    if isinstance(db, pymysql.connections.Connection):
        con = db
    else:
        con = connect(db)

    cursor = con.cursor(cursors.DictCursor)

    # Construct SQL expression
    sql = f"SELECT * FROM {table}"

    # Build conditions list
    filter_clauses = _cond_to_filter(cond) or []

    # Add deleted = 0 condition
    if not deleted:
        filter_clauses = [f"{table}.deleted = 0"] + list(filter_clauses)

    # Convert to SQL string
    if filter_clauses:
        sql += " WHERE " + " AND ".join(f"({c})" for c in filter_clauses)

    # Execute SQL query
    cursor.execute(sql)

    # Fetch the result as a DataFrame
    result = pd.DataFrame(cursor.fetchall())

    # Close the cursor
    cursor.close()

    # Close the connection if a new connection was established
    if not isinstance(db, pymysql.connections.Connection):
        con.close()

    # Compact: add table/database columns and normalise type column name
    if compact and not result.empty:
        result = result.copy()
        result["table"] = table
        if isinstance(db, str):
            result["database"] = db
        type_cols = [col for col in result.columns if re.match(r"^[a-z]+type$", col)]
        if len(type_cols) == 1:
            result["type"] = result[type_cols[0]]
            result = result.drop(columns=[type_cols[0]])

    return result


def name(con):
    
    """
    Retrieve the database name from the MySQL connection.

    :param con: (pymysql.connections.Connection) The MySQL database connection.
    :return: str or None
        The name of the connected database, or None if no database is selected.

    """
    with con.cursor() as cursor:
        cursor.execute("SELECT DATABASE();")
        result = cursor.fetchone()
        return result[0] if result else None


def databases(epi=False):
    
    """
    Retrieve a list of databases, optionally filtered by prefix.

    :param epi: (bool) If True, filter databases to those starting with 'epi_'.
                If False, return all databases. Default is False.
    :return: list
        A list of database names.
    """
    con = connect()
    with con.cursor() as cursor:
        cursor.execute("SHOW DATABASES;")
        dbs = cursor.fetchall()

    if epi:
        dbs = [db[0] for db in dbs if db[0].startswith("epi_")]

    return dbs


def condition(table, field, values):
    
    """
    Create a filter condition for a field based on specified values.

    :param table: (str) The name of the table.
    :param field: (str) The name of the field to filter.
    :param values: (list) A list of values to use in the filter condition.
                   Supported value types: int, float, str.
    :return: str
        A filter condition statement.
    """
    if all(isinstance(val, (int, float)) for val in values):
        value_str = f"({','.join(map(str, values))})"
    elif all(isinstance(val, str) for val in values):
        value_str = f"('{','.join(values)}')"
    else:
        raise ValueError("Unsupported value types in the list")

    statement = f"{table}.{field} IN {value_str}"
    return statement


def geolocations(db=None, itemtype="geolocations"):
    
    """
    Retrieve geolocations data for a given database.

    :param db: (str or None) The name of the database. If None, the default database will be used.
    :param itemtype: (str) The item type for geolocations. Default is "geolocations".
    :return: pandas.DataFrame
        A DataFrame containing the retrieved geolocations data.
        
    """
    # TODO: Use connect(), see annotations()
    engine = create_engine(f"mysql+pymysql://{os.environ.get('epi_username')}:{os.environ.get('epi_password')}@{os.environ.get('epi_host')}:{os.environ.get('epi_port')}/{db}")

    sql = f"""
        SELECT
          articles_id,
          id AS item_id,
          sortno,
          published,
          CAST(JSON_VALUE(`value`, '$.lat') AS DOUBLE) AS lat,
          CAST(JSON_VALUE(`value`, '$.lng') AS DOUBLE) AS lng
        FROM items WHERE
          itemtype = '{itemtype}' AND
          deleted=0
    """

    table = pd.read_sql_query(sql, engine)

    return table


def annotations(db, tables=['items', 'links'], filter={}):
    
    """
    Retrieve article annotations from items and links.

    Data from the items, properties, types, articles, and links tables will be joined.

    :param db: (str or None) The name of the database. If None, the default database will be used.
    :param filter: (dict) Filter by itemtype, linktype, propertytype, articletype, or projecttype by assigning
                          the respective keys with a list of allowed values.
    :param tables: (list or str) Add 'items' or 'links' to the list to retrieve annotations from the respective tables.
    :return: pandas.DataFrame
        A DataFrame containing annotations
    """

    # Defaults
    tables = [tables] if not isinstance(tables, list) else tables

    # Get connection
    db = os.environ.get("epi_dbname") if db is None else db
    con = connect(db)
    cursor = con.cursor(cursors.DictCursor)

    # Filter construction method
    def typeFilter(filter, tablename, colname):
        filter = filter.get(colname, [])
        filter = [filter] if not isinstance(filter, list) else filter
        if len(filter) > 0:
            filter = ['"' + x + '"' for x in filter]
            filter = "AND " + tablename + "." + colname + " IN (" + ",".join(filter) + ")"
            return filter
        else:
            return ""

    items = pd.DataFrame()
    if ('items' in tables):
        # Construct items SQL expression
        sql_items = f"""
           SELECT
                items.itemtype, items.sortno, items.properties_id ,
                properties.lemma, properties.name, properties.norm_iri AS properties_iri, 
                properties.propertytype,            
                items.articles_id, articles.signature as articles_signature, articles.norm_iri AS articles_iri,
                articles.articletype,
                projects.id AS projects_id, projects.signature AS projects_signature, projects.norm_iri AS projects_iri,
                projects.projecttype
           FROM items 
           INNER JOIN properties ON items.properties_id = properties.id AND properties.deleted=0 {typeFilter(filter,'properties','propertytype')}
           INNER JOIN articles ON items.articles_id = articles.id AND articles.deleted=0 {typeFilter(filter,'articles','articletype')}
           INNER JOIN projects ON articles.projects_id = projects.id AND projects.deleted=0 {typeFilter(filter,'projects','projecttype')}
           WHERE items.deleted=0 {typeFilter(filter,'items','itemtype')}
        """


        # Execute SQL query
        cursor.execute(sql_items)
        items = pd.DataFrame(cursor.fetchall())

    links = pd.DataFrame()
    if ('links' in tables):
        # Construct links SQL expression
        sql_links = f"""
               SELECT
                    links.from_tagname AS linktype, links.to_id AS properties_id,
                    properties.lemma, properties.name, properties.norm_iri AS properties_iri, 
                    properties.propertytype,            
                    links.root_id AS articles_id, articles.signature as articles_signature, articles.norm_iri AS articles_iri,
                    articles.articletype,
                    projects.id AS projects_id, projects.signature AS projects_signature, projects.norm_iri AS projects_iri,
                    projects.projecttype
               FROM links
               INNER JOIN properties ON links.to_id = properties.id AND links.to_tab='properties' AND properties.deleted=0  {typeFilter(filter,'properties','propertytype')}
               INNER JOIN articles ON links.root_id = articles.id AND links.root_tab='articles' AND articles.deleted=0  {typeFilter(filter,'articles','articletype')}           
               INNER JOIN projects ON articles.projects_id = projects.id AND projects.deleted=0  {typeFilter(filter,'projects','projecttype')}
               WHERE links.deleted=0  {typeFilter(filter,'links','from_tagname')}
            """

        # Execute SQL query
        cursor.execute(sql_links)
        links = pd.DataFrame(cursor.fetchall())

    # Close the cursor
    cursor.close()
    con.close()

    annotations =  pd.concat([items, links])
    annotations['db'] = db

    return annotations


def properties(db):
    
    """
    Retrieve properties

    The result includes the properties and their hierarchical relationships.

    TODO: revise

    :param db: (str or None) The name of the database. If None, the default database will be used.
    :return: pandas.DataFrame
        A DataFrame containing the retrieved codes.
    """
    con = connect(db)  # Use the connect function to get the connection

    # Check if the result is a tuple (connection, databasename)
    if isinstance(con, tuple):
        con, databasename = con
    else:
        databasename = db

    properties = table("properties", db=con)

    if isinstance(db, str):
        con.close()

    # Filter properties without related_id (top-level properties)
    codes = properties[properties['related_id'].isna()][[
        'id', 'parent_id', 'propertytype', 'lemma', 'name',
        'norm_data', 'norm_iri', 'level', 'lft', 'rght'
    ]]

    # Remove duplicates in the 'propertytype' column
    codes = codes.drop_duplicates('propertytype')

    # Create propertytypes DataFrame with unique property types
    propertytypes = codes.assign(
        level=-1,
        id=lambda x: -x.groupby('propertytype').cumcount() - 1
    )

    # Merge propertytypes with codes and handle parent_id
    codes = codes.merge(
        propertytypes[['id', 'propertytype']],
        left_on='propertytype',
        right_on='propertytype',
        suffixes=('', '_propertytypes')
    ).assign(
        parent_id=lambda x: x['id_propertytypes'].combine_first(x['parent_id'])
    ).drop(columns=['id_propertytypes'])

    # Concatenate propertytypes and codes, adjust hierarchical structure
    codes = pd.concat([
        propertytypes,
        codes
    ]).groupby('propertytype').apply(lambda x: fix_lft_rght(x)).reset_index(drop=True)

    # Fill missing lemma with name
    codes['lemma'] = codes['lemma'].fillna(codes['name'])

    # Add database name to the DataFrame
    codes['db'] = databasename

    return codes

def fix_lft_rght(df):
    if df["level"].iloc[0] == -1:
        df["lft"] = df["lft"].min() - 1
        df["rght"] = df["rght"].max() + 1
    return df


def fetch(table_name: str, params=None, db=None):
    """
    Fetch entity data such as articles, projects or properties using direct database access.

    Returns all data belonging to all entities matched by the params.

    Mirrors db_fetch() from fetch.R.

    :param table_name: (str) The table name (e.g., "articles")
    :param params: (dict) A dictionary of query conditions passed to db.table()
    :param db: (str or list) The database name or a list of database names
    :return: (pandas.DataFrame) Data from the database
    """
    if params is None:
        params = {}

    if utils.is_multi_db(db):
        data = pd.DataFrame()
        for single_db in utils.iter_dbs(db):
            check.is_db(single_db)
            data = pd.concat([data, fetch(table_name, params, single_db)], ignore_index=True)
        return data

    if db is not None:
        check.is_db(db)

    df_root = table(table_name, cond=params, db=db, compact=True)
    data = df_root.copy()

    # Get contained article data (mirrors db_fetch articles block in fetch.R)
    if table_name == "articles" and not df_root.empty:
        if "projects_id" in df_root.columns:
            df_root = df_root.rename(columns={"projects_id": "project"})
        if "projects_id" in data.columns:
            data = data.rename(columns={"projects_id": "project"})

        root_ids = df_root["id"].dropna().tolist() if "id" in df_root.columns else []
        if root_ids:
            df_sections = table("sections", cond={"articles_id": root_ids}, db=db, compact=True)
            data = pd.concat([data, df_sections], ignore_index=True)

            df_items = table("items", cond={"articles_id": root_ids}, db=db, compact=True)
            if "properties_id" in df_items.columns:
                df_items = df_items.rename(columns={"properties_id": "property"})
            data = pd.concat([data, df_items], ignore_index=True)

            if "property" in df_items.columns:
                item_props = df_items["property"].dropna().unique().tolist()
                if item_props:
                    df_props = table("properties", cond={"id": item_props}, db=db, compact=True)
                    data = pd.concat([data, df_props], ignore_index=True)

            df_footnotes = table(
                "footnotes", cond={"root_tab": "articles", "root_id": root_ids}, db=db, compact=True
            )
            data = pd.concat([data, df_footnotes], ignore_index=True)

            df_links = table(
                "links", cond={"root_tab": "articles", "root_id": root_ids}, db=db, compact=True
            )
            data = pd.concat([data, df_links], ignore_index=True)

            if not df_links.empty and {"to_tab", "to_id"}.issubset(df_links.columns):
                links_props = df_links[
                    (df_links["to_tab"] == "properties") & (df_links["to_id"].notna())
                ]
                if not links_props.empty:
                    df_props = table(
                        "properties", cond={"id": links_props["to_id"].tolist()}, db=db, compact=True
                    )
                    data = pd.concat([data, df_props], ignore_index=True)

        if "project" in df_root.columns:
            project_ids = df_root["project"].dropna().unique().tolist()
            if project_ids:
                df_projects = table("projects", cond={"id": project_ids}, db=db, compact=True)
                data = pd.concat([data, df_projects], ignore_index=True)

    # Add property ancestors (mirrors the while loop in db_fetch() from fetch.R)
    while True:
        if "table" not in data.columns or "id" not in data.columns:
            break

        props_all = data[data["table"] == "properties"].drop_duplicates()
        if props_all.empty or "parent_id" not in props_all.columns:
            break

        existing_ids = set(props_all["id"].dropna().tolist())
        missing_ids = [
            pid for pid in props_all["parent_id"].dropna().unique().tolist()
            if pid not in existing_ids
        ]
        if not missing_ids:
            break

        props_missing = table("properties", cond={"id": missing_ids}, db=db, compact=True)
        if props_missing.empty:
            break

        data = pd.concat([data, props_missing], ignore_index=True)

    data = utils.drop_empty_columns(data)
    data = utils.move_cols_to_front(data, ["database", "table", "type", "id"])
    return data



  

