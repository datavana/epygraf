# Fetch data from Epigraf

import epygraf as epi

#%%

epi.db.setup(
    host="127.0.0.3",
    port=3306,
    username="root",
    password="root"
)

#%%
ram = epi.db.fetch("articles", db = "epi_movies")

#%%

arts = epi.distill.articles(ram, ["name","signature"], item_type = "text", item_cols = ["content"])
