import asyncio
from typing import Optional

from marvin.tools import Tool
from typing_extensions import Literal

from marvin_recipes.vectorstores.chroma import Chroma

QueryResultType = Literal["documents", "distances", "metadatas"]


async def query_chroma(
    query: str,
    collection: str = "marvin",
    n_results: int = 5,
    where: Optional[dict] = None,
    where_document: Optional[dict] = None,
    include: Optional[list[QueryResultType]] = None,
    max_characters: int = 2000,
) -> str:
    async with Chroma(collection) as chroma:
        results = await chroma.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include or ["documents"],
        )

    print(results)

    return "\n".join(
        [
            f"{i+1}. {', '.join(excerpt)}"
            for i, excerpt in enumerate(results["documents"])
        ]
    )[:max_characters]


class QueryChroma(Tool):
    """Tool for querying a Chroma index."""

    description: str = """
        Retrieve document excerpts from a knowledge-base given a query.
    """

    async def run(
        self,
        query: str,
        collection: str = "marvin",
        n_results: int = 5,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
        include: Optional[list[QueryResultType]] = None,
        max_characters: int = 2000,
    ) -> str:
        return await query_chroma(
            query, collection, n_results, where, where_document, include, max_characters
        )


class MultiQueryChroma(Tool):
    """Tool for querying a Chroma index."""

    description: str = """
        Retrieve document excerpts from a knowledge-base given a query.
    """

    async def run(
        self,
        queries: list[str],
        collection: str = "marvin",
        n_results: int = 5,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
        include: Optional[list[QueryResultType]] = None,
        max_characters: int = 2000,
        max_queries: int = 5,
    ) -> str:
        if len(queries) > max_queries:
            # make sure excerpts are not too short
            queries = queries[:max_queries]

        coros = [
            query_chroma(
                query,
                collection,
                n_results,
                where,
                where_document,
                include,
                max_characters // len(queries),
            )
            for query in queries
        ]
        return "\n\n".join(await asyncio.gather(*coros, return_exceptions=True))
