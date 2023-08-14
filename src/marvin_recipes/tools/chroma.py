import asyncio
from typing import Optional

from marvin.tools import Tool
from typing_extensions import Literal

from marvin_recipes.vectorstores.chroma import Chroma

QueryResultType = Literal["documents", "distances", "metadatas"]


async def query_chroma(
    query: str,
    collection: str = "marvin",
    n_results: int = 3,
    where: Optional[dict] = None,
    where_document: Optional[dict] = None,
    include: Optional[list[QueryResultType]] = None,
    max_characters: int = 2000,
    client_type: str = "base",
) -> str:
    async with Chroma(collection, client_type=client_type) as chroma:
        results = await chroma.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include or ["documents"],
        )

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
        n_results: int = 3,
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

    client_type: Literal["http", "base"] = "http"

    async def run(
        self,
        queries: list[str],
        collection: str = "marvin",
        n_results: int = 3,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
        include: Optional[list[QueryResultType]] = None,
        max_characters: int = 2000,
        max_queries: int = 3,
    ) -> str:
        if len(queries) > max_queries:
            # make sure excerpts are not too short
            queries = queries[:max_queries]

        coros = [
            query_chroma(
                query=query,
                collection=collection,
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=include,
                max_characters=max_characters // len(queries),
                client_type=self.client_type,
            )
            for query in queries
        ]
        return "\n\n".join(await asyncio.gather(*coros, return_exceptions=True))
