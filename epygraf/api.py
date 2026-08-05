import os
import re
import time
from urllib.parse import urlparse, urlunparse, urlencode
import pandas as pd
import io
import requests
from epygraf import base
from epygraf import utils
from epygraf import check
from tqdm import tqdm


def setup(apiserver, apitoken, verbose=False): 
    
    """
    Save API connection settings to environment variables.

    :param apiserver: (str) URL of the Epigraf server
                        (including https-protocol)
    :param apitoken: (str) Access token
    :param verbose: (bool) Show debug messages and the built URLs
                    (default is False)
    """
    settings = dict(locals())
    settings = {f"epi_{key}": str(value) for key, value in settings.items()}
    settings['epi_verbose'] = str(verbose).upper()
    os.environ.update(settings)


def silent(silent=False):
    """
    Set silent mode

    In silent mode, all user prompts are automatically confirmed.
    Be careful, this will skip the prompt to confirm operations
    on the live server.

    :param silent: (bool)
    """
    settings = dict()
    settings['epi_silent'] = str(silent).upper()
    os.environ.update(settings)

def buildurl(endpoint, query=None, database=None, extension="json"):
    
    """
    Build base URL.

    :param endpoint: (str) The endpoint, e.g. articles/import
    :param query: (dict or None) Query parameters for the endpoint
    :param database: (str or None) The database name
    :param extension: (str) Extension added to the URL path, defaults to json.
    :return: (str) The built URL
    """
    # Get server and token from the global settings
    server = os.getenv("epi_apiserver")
    token = os.getenv("epi_apitoken")
    verbose = os.getenv("epi_verbose") == "TRUE"
    silent = os.getenv("epi_silent") == "TRUE"

    parsed_url = urlparse(server)
    parsed_query = dict(parsed_url.query)
    parsed_query["token"] = token    
    
    # Add query parameters
    if query is not None:
        parsed_query.update(query)
    
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    # Merge endpoint URL (if it contains query params or an extension)
    parsed_endpoint = urlparse(endpoint)
    parsed_query.update(dict(parsed_endpoint.query))
    endpoint = parsed_endpoint.path
    endpoint_extension = utils.get_extension(endpoint)

    if endpoint_extension != "":
        extension = ""
    elif extension is None:
        extension = ""
    elif extension is not None and not extension.startswith("."):
        extension = "." + extension

    if database is not None:
        path = f"epi/{database}{endpoint}{extension}"
    else:
        path = f"{endpoint}{extension}"
    
    parsed_url = parsed_url._replace(path=path, query=urlencode(parsed_query))
    parsed_url = urlunparse(parsed_url)

    if verbose and not silent:
        print(parsed_url)

    return parsed_url


# Create and execute a job
def job_create(endpoint, params, database, payload=None):
    """
    Create and execute a job

    :param endpoint: (str) The endpoint supporting job creation.
    :param params: (dict) Query parameters.
    :param database: (str) The selected database.
    :param payload: (object or None) The data posted to the job endpoint.
    :return: (dict) A dictionary containing the following keys:
                    polling, error, message, data, solved, downloads.
    """
    server = os.getenv("epi_apiserver")
    verbose = True if os.getenv("epi_verbose") == "TRUE" else False
    silent = True if os.getenv("epi_silent") == "TRUE" else False

    if not silent:
        print(f"Creating job on server {server}")

    # 1. Create job
    url = buildurl(endpoint, params, database)

    if (not utils.is_local_server(server)):
        utils.confirm_action()

    if verbose:
        resp = requests.post(url, json=payload, cookies={"XDEBUG_SESSION": "XDEBUG_ECLIPSE"})
    else:
        resp = requests.post(url, json=payload)

    body = resp.json()
    job_id = body.get("job_id", None)

    error = False
    message = None

    # Request error
    if resp.status_code != 200:
        error = True
        message = body.get("error", {}).get("message", None)

    # Job error
    elif not body.get("success", True):
        error = True
        message = body.get("message", None)

    # No job ID
    elif job_id is None:
        error = True
        message = "No job ID found."

    if error:
        raise Exception(f"Could not create job: {message}")

    if message is not None:
        print(message)

    # 2. Execute job
    return job_execute(job_id)


# Execute a job
def job_execute(job_id):
    """
    Execute a job.

    :param job_id: (str) The job ID
    :return: (dict) A dictionary containing the following keys:
                    polling, error, message, data, solved, downloads.
    """

    verbose = True if os.getenv("epi_verbose") == "TRUE" else False
    print(f"Starting job {job_id}.")

    url = buildurl(f"jobs/execute/{job_id}", None, None)

    result = []
    polling = True
    error = None
    message = None

    while polling:
        if verbose:
            resp = requests.post(url, cookies={"XDEBUG_SESSION": "XDEBUG_ECLIPSE"})
        else:
            resp = requests.post(url)

        body = resp.json()
        newresult = None

        # Request error
        if resp.status_code != 200:
            polling = False
            error = True
            message = body.get("error", {}).get("message", None)

        # Job error
        elif body.get("job", {}).get("error", False):
            polling = False
            error = True
            message = body.get("job", {}).get("error", None)

        # Continue
        elif "job" in body and "nextUrl" in body["job"]:
            polling = True
            error = False
            message = body.get("job", {}).get("message", None)
            newresult = body.get("job", {}).get("result", None)

            delay = body.get("job", {}).get("delay", 0)
            if (delay > 0):
                time.sleep(1)

            progressCurrent = body.get("job", {}).get("progress", None)
            progressMax = body.get("job", {}).get("progressmax", -1)
            if progressMax == -1:
                print(f"Progress {progressCurrent}")
            else:
                print(f"Progress {progressCurrent} / {progressMax}")

        # Finished
        else:
            polling = False
            error = False
            message = body.get("message", None)
            newresult = body.get("job", {}).get("result", None)

        # Output
        if error:
            raise Exception(f"Could not execute job: {message}")

        if newresult is not None:
            result.append(newresult)

        if message is not None:
            print(message)

    # Extract solved IDs
    solved = []
    for x in result:
        if "solved" in x and x["solved"] is not None:
            solved.append(pd.DataFrame(x["solved"]))

    # Remove solved from result
    for x in result:
        x.pop("solved", None)

    if len(solved) > 0:
        solved = pd.concat(solved, ignore_index=True).drop_duplicates()
    else:
        solved = pd.DataFrame()


    # Extract downloads
    downloads = []
    for x in result:
        if "downloads" in x and x["downloads"] is not None:
            dfs = [pd.DataFrame(d) for d in x["downloads"]]
            if dfs:
                downloads.append(pd.concat(dfs, ignore_index=True))

    # Remove downloads from result
    for x in result:
        x.pop("downloads", None)

    if len(downloads) > 0:
        downloads = pd.concat(downloads, ignore_index=True).drop_duplicates()
    else:
        downloads = pd.DataFrame()


    # Final result structure
    result = {
        "polling": polling,
        "error": error,
        "message": message,
        "data": result,
        "solved": solved,
        "downloads": downloads,
    }

    # TODO: use Python class to wrap result
    return result


def table(endpoint, params=None, db=None, maxpages=1, compact=False, silent=False):

    """
    Download tabular data.

    :param endpoint: (str) The endpoint path (e.g. "articles/index" or "articles/view/1")
    :param params: (dict) A named dictionary of query parameters
    :param db: (str or list) The database name.
               Provide a list of database names to fetch and row-bind data from multiple databases.
               In that case compact is automatically set to True.
    :param maxpages: (int) Maximum number of pages to request.
                    Set to 1 for non-paginated tables.
    :param compact: (bool) Whether to rename type columns to `type` and to add `table` and `database` columns.
    :param silent: (bool) Whether to output status messages
    :return: (pandas.DataFrame) The downloaded tabular data
    """
    # If db is a list of databases, iterate and bind rows
    if utils.is_multi_db(db):
        db_list = utils.iter_dbs(db)
        data = pd.DataFrame()
        for single_db in db_list:
            data = pd.concat(
                [data, table(endpoint, params, single_db, maxpages, compact=True, silent=silent)],
                ignore_index=True,
            )
        return to_epitable(data, {"endpoint": endpoint, "params": params, "db": db_list})

    verbose = True if os.getenv("epi_verbose") == "TRUE" else False

    data = pd.DataFrame()
    page = 1

    fetchmore = True
    while fetchmore:
        if params is None:
            params = {}
        params["page"] = page
        url = buildurl(endpoint, params, db, "csv")

        if not silent:
            if maxpages == 1:
                print(f"Fetching data from {endpoint}.")
            else:
                print(f"Fetching page {page} from {endpoint}.")
        message = None

        try:
            if verbose:
                resp = requests.get(url, cookies={'XDEBUG_SESSION': 'XDEBUG_ECLIPSE'})
            else:
                resp = requests.get(url)

            if resp.status_code == 200:
                body = resp.text
                rows = pd.read_csv(io.StringIO(body), delimiter=";", dtype=str)
            elif resp.status_code == 404:
                message = "No more data found."
                rows = pd.DataFrame()
            else:
                rows = pd.DataFrame()
                message = f"Error {resp.status_code}: {resp.text}"

        except Exception as e:
            message = str(e)
            rows = pd.DataFrame()

        if message is not None:
            print(message)

        if not rows.empty:
            data = pd.concat([data, rows], ignore_index=True)
            fetchmore = page < maxpages
            page += 1
        else:
            fetchmore = False

    if not silent:
        print(f"Fetched {data.shape[0]} records from {endpoint}.")

    # Convert columns to appropriate types
    data = data.convert_dtypes()

    # Compact: add database/table columns and normalise type column name
    if compact and not data.empty:
        if db is not None:
            data["database"] = db
        table_default = endpoint.split("/", 1)[0]
        if "id" in data.columns:
            table_from_id = data["id"].astype("string").str.extract(r"^([a-z]+)-", expand=False)
        else:
            table_from_id = pd.Series([None] * len(data), dtype="string")
        if "table" not in data.columns:
            data["table"] = table_from_id.fillna(table_default)
        else:
            data["table"] = data["table"].astype("string").fillna(table_from_id).fillna(table_default)
        type_cols = [col for col in data.columns if re.match(r"^[a-z]+type$", col)]
        if len(type_cols) == 1:
            data["type"] = data[type_cols[0]]
            data = data.drop(columns=[type_cols[0]])

    data = to_epitable(data, {"endpoint": endpoint, "params": params, "db": db})
    return data

def fetch(table_name: str, params=None, db=None, maxpages: int = 1):
    """
    Fetch entity data such as articles, projects or properties from the API.

    Returns all data belonging to all entities matched by the params.
    The procedure corresponds to calling the index action with columns=0.

    Mirrors api_fetch() from fetch.R.

    :param table_name: (str) The table name (e.g., "articles")
    :param params: (dict) A dictionary of query parameters
    :param db: (str or list) The database name or a list of database names
    :param maxpages: (int) Maximum number of pages to request
    :return: (pandas.DataFrame) Data from the API
    """
    if params is None:
        params = {}
    else:
        params = dict(params)

    params["columns"] = "0"
    params["idents"] = "id"

    data = table(table_name, params, db, maxpages, compact=True)
    data = data.drop_duplicates(ignore_index=True)
    data = utils.move_cols_to_front(data, ["database", "table", "type", "id"])
    return data


def fetch_table(table_name: str, columns=None, params=None, db=None, maxpages: int = 1):
    """
    Fetch tables such as articles, projects, or properties.

    Returns a row with defined columns for each record matched by the params.

    :param table_name: The table name (e.g., "articles")
    :param columns: A list of column names
    :param params: A dictionary of query parameters
    :param db: The database name or a list of database names
    :param maxpages: Maximum number of pages to request. Set to 1 for non-paginated tables.
    :return: Data from the API
    """
    if columns is None:
        columns = []
    if params is None:
        params = {}
    else:
        params = dict(params)

    # id is always included; preserve insertion order, no duplicates
    unique_columns = list(dict.fromkeys(["id", *list(columns)]))
    params["columns"] = ",".join(unique_columns)
    params["idents"] = "id"

    # api.table handles multi-db internally
    return table(table_name, params, db, maxpages)


def fetch_entity(ids, params=None, db=None, silent: bool = False):
    """
    Fetch entities such as single articles, projects, or properties.

    Returns all data belonging to the entity identified by ID.

    :param ids: A list of IDs or a DataFrame containing an 'id' column.
                IDs are of the form <table>-<row>, e.g. "articles-123".
    :param params: A dictionary of query parameters
    :param db: The database name. Leave empty when providing a DataFrame produced by fetch_table().
               In this case the database name will be extracted from the DataFrame.
    :param silent: Whether to suppress the progress bar
    :return: Data from the API
    """
    if params is None:
        params = {}
    else:
        params = dict(params)

    # Extract database name from DataFrame metadata
    if db is None and isinstance(ids, pd.DataFrame) and isinstance(ids.attrs.get("epi_source"), dict):
        db = ids.attrs["epi_source"].get("db")

    if db is not None:
        check.is_db(db)

    # Normalise ids to a plain list
    if isinstance(ids, pd.DataFrame):
        if "id" not in ids.columns:
            raise ValueError("DataFrame input must contain an 'id' column.")
        ids = ids["id"].tolist()
    elif isinstance(ids, pd.Series):
        ids = ids.tolist()
    elif isinstance(ids, tuple):
        ids = list(ids)
    elif not isinstance(ids, list):
        ids = [ids]

    if len(ids) == 0:
        return to_epitable(pd.DataFrame(), {"params": params, "db": db})

    if len(ids) > 1:
        data = pd.DataFrame()
        iterator = ids if silent else tqdm(ids, desc="Fetching entities")
        for id_val in iterator:
            data = pd.concat([data, fetch_entity(id_val, params, db, silent=True)], ignore_index=True)
        return data

    id = ids[0]
    check.is_id(id)
    tbl, row_id = id.split("-", 1)

    data = table(f"{tbl}/view/{row_id}", params, db, 1, silent=silent)

    if "id" in data.columns:
        data[["table", "row"]] = data["id"].str.split("-", n=1, expand=True)

    data = to_epitable(data)
    return data


def patch(data, database, table=None, type=None, wide=True):
    """
    Update entities in the database using the API.
    Existing entities will be updated, missing entities will be created.
    The function supports uploading all data related to articles:
    articles, sections, items, links, footnotes, properties, projects, users, types.
    The IRI path in the ID column of the dataframe must contain the specific table name.

    :param data: (pandas.DataFrame) A dataframe with the column `id`.
                 Additional columns such as `norm_data` will be written to the entity.
                 The id must either be a valid IRI path (e.g. `properties/objecttypes/xxx`)
                 or an id prefixed by the table name (e.g. `properties-12`).
                 Patching properties with prefixed ids requires a `type` column that contains the property type.
                 If wide is set to true (default), column names prefixed with table names are extracted.
    :param database: (str) The database name.
    :param table: (str or None) Optional: Check that the data only contains rows for a specific table.
    :param type: (str or None) Optional: Check that the data only contains rows with a specific type.
    :param wide: (bool) Convert wide format to long format.
                        If true, column names prefixed with "properties", "items", "sections", "articles"
                        and "projects" followed by a dot (e.g. `properties.id`, `properties.lemma`)
                        will be extracted and patched as additional entities.
        :return: (dict) A dictionary containing the following keys:
                    polling, error, message, data, solved, downloads.
    """
    
    if wide:
        data = base.wide_to_long(data)

    # TODO:
    # stopifnot(epi_is_iripath(data$id, table, type) | epi_is_id(data$id, table))

    # Reorder
    if "id" in data.columns:
        data = data[["id"] + [col for col in data.columns if col != "id"]]

    # Remove complete empty columns
    data = data.loc[:, data.notna().all()]

    # Remove rows where all values are NA
    data = data.dropna(how="all")

    if data.empty:
        raise Exception("Data is empty or contains NA values.")

    if len(data.columns) == 1 and "id" in data.columns:
        raise Exception("Skipped, the data only contains the ID column.")

    print(f"Uploading {len(data)} rows.")

    return job_create("articles/import", None, database, {"data": data.to_dict(orient="records")})

def to_epitable(data: pd.DataFrame, source: dict = None) -> pd.DataFrame:
    """
    Add the epigraf source and type attributes to the DataFrame

    :param data: A pandas DataFrame
    :param source: A dictionary of source parameters, containing endpoint, parameters, and database name
    :return: Modified DataFrame with metadata in the attrs property
    """
    # Set source
    if source is not None:
        data.attrs["epi_source"] = source

    # Reorder columns
    id_cols = [col for col in  ["database", "table", "row", "type", "norm_iri"] if col in data.columns]
    belongsto_id_cols = [col for col in data.columns if col.endswith("id")]
    belongsto_name_cols = [col for col in ["project","article","section","item","property","footnote"] if col in data.columns]
    state_cols = [col for col in data.columns if col.startswith(("created", "modified"))]
    content_cols = [col for col in data.columns if col not in id_cols + belongsto_id_cols + belongsto_name_cols + state_cols]

    ordered_cols = id_cols + content_cols + belongsto_name_cols + belongsto_id_cols + state_cols
    data = data[ordered_cols]

    # Add Epigraf type attribute
    data.attrs["epi_type"] = "table"
    return data