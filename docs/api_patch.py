# Patch data to Epigraf

import pandas as pd
import epygraf as epi

#%%

epi.api.setup(
    "https://epigraf.uni-muenster.de",
    "testapitoken"
)

#%%

df = pd.DataFrame({
    "id":               ["items/categories/moview~001~categories~genre"],
    "articles_id":      ["articles/default/movies~001"],
    "sections.id":      ["sections/categories/movies~001~categories"],
    "sections.name" :   ["Genres"],
    "properties.id":    ["properties/categories/fancygenre"],
    "properties.lemma": ["Fancy Genre"]
})

epi.api.patch(df, database="movies")
