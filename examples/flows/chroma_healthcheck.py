from marvin_recipes.vectorstores.chroma import Chroma
from prefect import flow


@flow
async def test_connection(client_type: str = "http"):
    async with Chroma(client_type=client_type) as chroma:
        assert chroma.ok()
