import asyncio
from typing import Any

from marvin.components.ai_model import AIModel, ai_model
from marvin_recipes.documents import Document, document_to_excerpts
from prefect import flow, task, unmapped
from pydantic import BaseModel


@ai_model
class Location(BaseModel):
    city: str
    country: str


@ai_model
class Person(BaseModel):
    first_name: str
    last_name: str


METADATA_MODELS = [Location, Person]


@task(retries=1)
async def get_metadata_from_chunk(
    doc: Document,
    metadata_model: AIModel,
) -> dict[str, Any]:
    return {
        "chunk": doc,
        "metadata": await metadata_model._extract_async(text_=doc.text),
    }


@flow
async def process_chunk(chunk):
    results = await get_metadata_from_chunk.map(
        doc=unmapped(chunk), metadata_model=METADATA_MODELS
    )

    print(f"writing {[await result.result() for result in results]} to database...")


@flow(log_prints=True)
async def process_document(document: Document):
    await asyncio.gather(
        *(process_chunk(chunk) for chunk in await document_to_excerpts(document))
    )


if __name__ == "__main__":
    asyncio.run(
        process_document(
            document=Document(
                text=(
                    "Lionel Messi is a soccer player from Rosario, Argentina and"
                    " he is considered one of the best players in the world."
                )
            )
        )
    )
