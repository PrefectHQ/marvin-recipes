from marvin_recipes.vectorstores.chroma import Chroma
from prefect import flow


@flow
async def test_connection():
    async with Chroma() as chroma:
        assert chroma.ok()
