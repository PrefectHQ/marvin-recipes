from functools import lru_cache

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Include, QueryResult
from chromadb.errors import IDAlreadyExistsError

import marvin
from marvin.utilities.async_utils import run_async
from marvin.utilities.documents import Document
from marvin.vectorstores.base import Vectorstore


@lru_cache
def get_client() -> "chromadb.Client":
    return chromadb.Client(
        # chroma 🤝 pydantic 🤝 marvin
        settings=chromadb.Settings(**marvin.settings.chroma.dict())
    )


class Chroma(Vectorstore):
    """
    A wrapper for chromadb.Client - can be used as a context manager
    """

    def __init__(
        self,
        collection_name: str = None,
        embedding_fn=None,
    ):
        import chromadb.utils.embedding_functions as embedding_functions

        self.client = get_client()
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

    def ok(self):
        try:
            response = self.client.get_version()
        except Exception as e:
            marvin.utilities.logging.get_logger().error(
                f"Cannot connect to Chroma: {e}"
            )
        if response:
            marvin.utilities.logging.get_logger().debug(
                f"Connected to Chroma v{response}"
            )
            return True
        return False
