from abc import ABC, abstractmethod


class Vectorstore(ABC):
    @abstractmethod
    async def query(self, *args, **kwargs):
        pass

    @abstractmethod
    async def upsert(self, *args, **kwargs):
        pass

    @abstractmethod
    async def delete(self, *args, **kwargs):
        pass

    @abstractmethod
    def ok(self, *args, **kwargs):
        pass

    def __enter__(self):
        self._in_context = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._in_context = False

    async def __aenter__(self):
        self._in_context = True
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._in_context = False
