import asyncio
from abc import ABC, abstractmethod

from marvin.utilities.types import LoggerMixin, MarvinBaseModel

from marvin_recipes.documents import Document
from marvin_recipes.utilities.collections import batched


class Loader(MarvinBaseModel, LoggerMixin, ABC):
    """A base class for loaders."""

    @abstractmethod
    async def load(self) -> list[Document]:
        pass

    class Config:
        arbitrary_types_allowed = True
        extra = "forbid"


class MultiLoader(Loader):
    loaders: list[Loader]

    async def load(self, batch_size: int = 5) -> list[Document]:
        return [
            doc
            for batch in batched(self.loaders, batch_size)
            for docs in await asyncio.gather(*(loader.load() for loader in batch))
            for doc in docs
        ]
