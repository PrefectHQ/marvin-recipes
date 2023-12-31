import re
from typing import Literal

import chromadb
import marvin
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Include, QueryResult
from chromadb.errors import IDAlreadyExistsError
from marvin.utilities.async_utils import run_async

import marvin_recipes
from marvin_recipes.documents import Document
from marvin_recipes.vectorstores.base import AsyncVectorstore


def get_client(client_type: Literal["http", "base"] = "http") -> "chromadb.Client":
    """Returns a certain type of chromadb client.

    marvin 🤝 pydantic 🤝 chroma
                 🤝
              fastapi
    """
    if client_type == "http":
        return chromadb.HttpClient(
            host=marvin_recipes.settings.chroma.chroma_server_host,
            port=marvin_recipes.settings.chroma.chroma_server_http_port,
        )
    else:
        return chromadb.Client(
            settings=chromadb.Settings(**marvin_recipes.settings.chroma.dict())
        )


class Chroma(AsyncVectorstore):
    """
    A wrapper for chromadb.Client - used as an async context manager
    """

    def __init__(
        self,
        collection_name: str = None,
        embedding_fn=None,
        client_type: Literal["http", "base"] = "base",
    ):
        import chromadb.utils.embedding_functions as embedding_functions

        self.client = get_client(client_type=client_type)
        self.embedding_fn = embedding_fn or embedding_functions.OpenAIEmbeddingFunction(
            api_key=marvin.settings.openai.api_key.get_secret_value()
        )
        self.collection: Collection = self.client.get_or_create_collection(
            name=collection_name or "marvin",
            embedding_function=self.embedding_fn,
        )
        self._in_context = False

    async def delete(
        self,
        ids: list[str] = None,
        where: dict = None,
        where_document: Document = None,
    ):
        await run_async(
            self.collection.delete,
            ids=ids,
            where=where,
            where_document=where_document,
        )

    async def add(self, documents: list[Document]) -> int:
        try:
            await run_async(
                self.collection.add,
                ids=[document.hash for document in documents],
                documents=[document.text for document in documents],
                metadatas=[document.metadata.dict() for document in documents],
            )
            return len(documents)
        except IDAlreadyExistsError:
            print("Documents already exist in the collection.")
            return 0

    async def query(
        self,
        query_embeddings: list[list[float]] = None,
        query_texts: list[str] = None,
        n_results: int = 10,
        where: dict = None,
        where_document: dict = None,
        include: "Include" = ["metadatas"],
        **kwargs,
    ) -> "QueryResult":
        return await run_async(
            self.collection.query,
            query_embeddings=query_embeddings,
            query_texts=query_texts,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include,
            **kwargs,
        )

    async def count(self) -> int:
        return await run_async(self.collection.count)

    async def upsert(self, documents: list[Document]):
        await run_async(
            self.collection.upsert,
            ids=[document.hash for document in documents],
            documents=[document.text for document in documents],
            metadatas=[document.metadata.dict() for document in documents],
        )

    async def reset_collection(self):
        await run_async(self.client.delete_collection, self.collection.name)
        self.collection = await run_async(
            self.client.create_collection,
            name=self.collection.name,
            embedding_function=self.embedding_fn,
        )

    def ok(self) -> bool:
        logger = marvin.utilities.logging.get_logger()
        try:
            version = self.client.get_version()
        except Exception as e:
            logger.error(f"Cannot connect to Chroma: {e}")
        if re.match(r"^\d+\.\d+\.\d+$", version):
            logger.debug(f"Connected to Chroma v{version}")
            return True
        return False
