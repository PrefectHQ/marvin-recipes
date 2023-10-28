import asyncio

import uvicorn
from fastapi import FastAPI
from marvin import ai_fn, ai_model
from pydantic import BaseModel

app = FastAPI()


@ai_fn
def generate_fruits(n: int) -> list[str]:
    """Generates a list of `n` fruits"""


@ai_fn
def generate_vegetables(n: int, color: str) -> list[str]:
    """Generates a list of `n` vegetables of color `color`"""


@ai_model
class Person(BaseModel):
    first_name: str
    last_name: str


app.add_api_route("/generate_fruits", generate_fruits, response_model=list[str])
app.add_api_route("/generate_vegetables", generate_vegetables, response_model=list[str])
app.add_api_route("/person/extract", Person)


async def main():
    config = uvicorn.Config(app)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
