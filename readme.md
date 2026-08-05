# Epygraf Python Package

The Epygraf package makes working with [Epigraf](https://digicademy.github.io/epigraf/) data from Python easier.

## Installation

You can install the package directly from GitHub:

```
pip install "git+https://github.com/datavana/epygraf.git#egg=epygraf"
```

If you are developing the package, clone the repository and from inside the epygraf folder call:
```
pip install -e .
```

If you want to work with the package and at the same time develop ist, 
clone the package repository and from the venv in the working directory call
(replace the path by the package path):

```
pip install -e  E:/Code/epigraf/packages/epygraf
```

When installing with the e-Option you can change code without reinstalling the package. 
In Jupyter, after installing or changing the package, don't forget to restart the kernel.
After the installation, you can use the package by `import epygraf as epi`.

## Usage

There are two ways to access Epigraf data: 

- **API**: Used to access data and create jobs from outside the server. 
- **Database**: Presumes you have a direct connection to the database server, e.g. in a development environment. 

## Access the Epigraf API

Please be aware: The API is under development and responds at a cosy pace. Please don't stress the servers.

The endpoints for accessing article data are documented in the [Epigraf help](https://epigraf.inschriften.net/help/epiweb-api). 
To get an access token for nonpublic data access follow the instructions in the help. 

After loading the epygraf package, you configure the connection to the API:

```
import epygraf as epi 

epi_apiserver = "https://epigraf.uni-muenster.de"
epi_apitoken = "YOURAPITOKEN"

epi.api.setup(epi_apiserver, epi_apitoken)
```

The access token is like a password, don't show it to anyone and make sure it is not printed in any logs or outputs.

Note: If you are working as a developer in a local environment, use the URL https://127.0.0.1/. 
The api_setup()-function provides a third parameter for enabling debug output.

If you get an "Error 401" when using the following methods, check your permissions.


## Reading data 

To warm up, get some article data. 
Data is always delivered in chunks, each chunk is called a page. 
The `limit` parameter tells the API to return 5 articles per page.
The `maxpages` parameter defines that fetching is stopped after one page.
Fetching is always stopped if there is no more data.

```
ram = epi.api.fetch("articles", params = {'limit':5}, db="epi_movies", maxpages=1)
```

The data come in the Relation-Article-Model-format. 
That means all pieces of an article are returned as rows.  

Use the distill-function to get some cozy data.
For example, extract all properties of type "categories" from the RAM data:

```
epi.distill.properties(ram, "categories")
```

Or extract the list of articles:

```
epi.distill.articles(ram, ["signature", "name"])
```

## Writing data

You can create or update data with `api.patch()`. The function expects data in the Relational Article Model-format.
The following command creates one categorie "Western" with the IRI "properties/categories/western" in the database epi_movies.

```

properties = pd.DataFrame({
    "id": ["properties/categories/western"],
    "lemma": ["Western"],
})


epi.api.patch(properties, database = "epi_movies")

```

If a property with the given IRI path already exists, it will not be created, but updated. This way you can change the labels.

The property types, "categories" in the example,  need to be configured in Epigraf. 
Thereafter, you can see the new properties in Epigraf by clicking the categories menu button. 

For more complex data, use the craft functions to map your data frames to the RAM.


## Database functions

Given you have direct access to an Epigraf server, 
you can show all article records from the epi_all-database 
by calling :

```
import epygraf as epi

epi.db.table("articles", "epi_all")
```

If your server runs under different settings than default, 
setup the connection settings first:

```
epi.db.setup(
    host="localhost", 
    port=3306, 
    username="root", 
    password="root" 
)
```

The table method returns a pandas dataframe, thus,
you can directly analyze the data:

```
ram = epi.db.table("articles")
ram.articletype.value_counts()
```

# Build the package

```
pip install build
python -m build
```

To install the new version, uninstall the old one first  `pip uninstall epygraf`.