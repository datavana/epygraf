# fetch data from epigraf

import epygraf as epi

#%%

epi.api.setup(
    "https://epigraf.uni-muenster.de",
    "testapitoken"
)

#%%

ram = epi.api.fetch("articles", db = "epi_movies")

arts = epi.distill.articles(ram, ["name","signature"], item_type = "text", item_cols = ["content"])
