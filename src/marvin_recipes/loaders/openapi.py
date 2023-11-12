from typing import List

from marvin.tools.openapi import parse_spec_to_human_readable

from marvin_recipes.documents import Document, document_to_excerpts
from marvin_recipes.loaders.base import Loader


class OpenAPISpecLoader(Loader):
    """A loader that loads documents from a OpenAPI spec URL."""

    openapi_spec_url: str

    async def load(self) -> List[Document]:
        return await document_to_excerpts(
            document=Document(
                text=await parse_spec_to_human_readable(self.openapi_spec_url)
            ),
        )
