# marvin-recipes

## to use this repo
ensure your OpenAI API key is in your environment
```bash
echo $OPENAI_API_KEY

# or

cat .env | grep MARVIN_OPENAI_API_KEY
```

get the code
```bash
git clone https://github.com/PrefectHQ/marvin-recipes.git
cd marvin-recipes
```

start a virtual environment and install deps
```bash
conda create -n marvin-recipes python=3.11 -y
conda activate marvin-recipes
pip install .
```


## build a local vectorstore with marvin and prefect
install some extras
```bash
pip install ".[chroma, loaders, prefect]"
```

put the sample db where the chroma client expects it
```bash
mkdir chroma
cp db/chroma.sqlite3 chroma/
```

[**optional**] creating a Chroma client will initialize a local index you can query
```python
# ipython gives you an event loop 🙂
from marvin_recipes.vectorstores.chroma import Chroma

async with Chroma() as chroma:
    chroma.ok() # you don't need to do this, just a sanity check
    print(await chroma.query(query_texts=["what are prefect blocks?"]))
```

### use the vectorstore
use the `QueryChroma` tool directly or give it to an `AIApplication` to use
```python
from marvin_recipes.tools.chroma import QueryChroma

print(await QueryChroma().run("what are prefect blocks?"))

# or

from marvin import AIApplication

knowledge_bot = AIApplication(
    name="knowledge_bot",
    tools=[QueryChroma(description="Finds answers about Prefect")],
)

knowledge_bot("what are prefect blocks?")
```

## optionally add some env vars to increase rate limits
```bash
MARVIN_GITHUB_TOKEN=your_github_token
MARVIN_DISCOURSE_API_KEY=your_discourse_api_key
```