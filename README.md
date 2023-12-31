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
# mamba, conda, etc - whatever you like
mamba create -n marvin-recipes python=3.11 -y
mamba activate marvin-recipes
pip install .
```


## build a local vectorstore with marvin and prefect
install some extras
```bash
pip install ".[chroma, loaders, prefect]"
```

you can now load documents into the vectorstore
```bash
python examples/flows/refresh_vectorstore.py
```

or instead just put a sample db in the `chroma` directory
```bash
mkdir chroma
cp db/chroma.sqlite3 chroma/
```

[**optional**] creating a `Chroma` instance will initialize a local index you can query
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
from marvin_recipes.tools.chroma import MultiQueryChroma

print(await MultiQueryChroma().run("what are prefect blocks and flows and tasks?"))

# or

from marvin import AIApplication

knowledge_bot = AIApplication(
    name="knowledge bot",
    description="A knowledge bot that can answer questions about Prefect",
    tools=[MultiQueryChroma(description="Find documents about Prefect")],
)

knowledge_bot("what are prefect blocks?")
```

### add your own tools for any type of retrieval augmented generation
```python
import marvin
from marvin import ai_fn, AIApplication
from marvin_recipes.tools.chroma import MultiQueryChroma

marvin.settings.log_level = "DEBUG"

def get_ip_address():
    import httpx
    return httpx.get("https://ip.me").text

def get_prime_factors(n: int) -> list[int]:
    """Get prime factors of n"""
    i = 2
    factors = []
    while i * i <= n:
        if n % i:
            i += 1
        else:
            n //= i
            factors.append(i)
    if n > 1:
        factors.append(n)
    return factors

@ai_fn(model="gpt-3.5-turbo")
def write_a_terrible_pun(topic: str) -> str:
    """Write a terrible pun about a topic.
    
    It should be so bad that it makes me want to cry.
    """

knowledge_bot = AIApplication(
    name="knowledge bot",
    description="A knowledge bot that can answer questions about <what you care about>",
    tools=[
        MultiQueryChroma(description="Use to find context about <whatever you've got in your vectorstore>"),
        get_ip_address,
        get_prime_factors,
        write_a_terrible_pun,
    ],
)
```

## optionally add some env vars to increase rate limits
```bash
MARVIN_GITHUB_TOKEN=your_github_token
MARVIN_DISCOURSE_API_KEY=your_discourse_api_key
```