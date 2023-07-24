import asyncio
import inspect
from typing import Callable, Optional

from jinja2 import Template
from pydantic import Field, confloat, validator
from typing_extensions import Literal

import marvin
from marvin.utilities.ids import DocumentID
from marvin.utilities.nlp import extract_keywords
from marvin.utilities.strings import (
    count_tokens,
    jinja_env,
    split_text,
)
from marvin.utilities.types import MarvinBaseModel

DocumentType = Literal["original", "excerpt", "summary"]


class DocumentMetadata(MarvinBaseModel):
    title: str = Field(default="[untitled]")
    link: str = Field(default="None")

    class Config:
        extra = "allow"
        arbitrary_types_allowed = True


class Document(MarvinBaseModel):
    """A source of information that is storable & searchable.

    Anything that can be represented as text can be stored as a document:
    web pages, git repos / issues, PDFs, and even just plain text files.
    """

    class Config:
        extra = "allow"

    id: str = Field(default_factory=DocumentID.new)
    parent_document_id: Optional[DocumentID] = Field(default=None)

    text: str = Field(..., description="Document text content.")
    embedding: Optional[list[float]] = Field(default=None)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)

    tokens: Optional[int] = Field(default=None)
    keywords: list[str] = Field(default_factory=list)

    @property
    def hash(self):
        return marvin.utilities.strings.hash_text(self.text)

    @validator("tokens", pre=True, always=True)
    def validate_tokens(cls, v, values):
        if not v:
            return count_tokens(values["text"])
        return v


EXCERPT_TEMPLATE = jinja_env.from_string(
    inspect.cleandoc("""The following is an excerpt from a document
        {% if document.metadata %}\n\n# Document metadata
        {{ document.metadata }}
        {% endif %}
        {% if document.keywords %}
        # Document keywords
        {{ document.keywords }}
        {% endif %}
        {% if minimap %}
        # Excerpt's location in document
        {{ minimap }}
        {% endif %}# Excerpt content: {{ excerpt_text }}""")  # noqa: E501
)


async def document_to_excerpts(
    document: "Document",
    excerpt_template: Template = None,
    chunk_tokens: int = 200,
    overlap: confloat(ge=0, le=1) = 0.1,
    **extra_template_kwargs,
) -> list["Document"]:
    """
    Create document excerpts by chunking the document text into regularly-sized
    chunks and adding a "minimap" directory to the top (if document is markdown).

    Args:
        excerpt_template: A jinja2 template to use for rendering the excerpt.
        chunk_tokens: The number of tokens to include in each excerpt.
        overlap: The fraction of overlap between each excerpt.

    """
    if not excerpt_template:
        excerpt_template = EXCERPT_TEMPLATE

    text_chunks = split_text(
        text=document.text,
        chunk_size=chunk_tokens,
        chunk_overlap=overlap,
        return_index=True,
    )

    return await asyncio.gather(
        *[
            _create_excerpt(
                document=document,
                text=text,
                index=i,
                excerpt_template=excerpt_template,
                **extra_template_kwargs,
            )
            for i, (text, chr) in enumerate(text_chunks)
        ]
    )


async def _create_excerpt(
    document: "Document",
    text: str,
    index: int,
    excerpt_template: Template,
    **extra_template_kwargs,
) -> "Document":
    keywords = extract_keywords(text)

    minimap = (
        create_minimap_fn(document.text)(index)
        if document.metadata.link and document.metadata.link.endswith(".md")
        else None
    )

    excerpt_text = await excerpt_template.render_async(
        document=document,
        excerpt_text=text,
        keywords=", ".join(keywords),
        minimap=minimap,
        **extra_template_kwargs,
    )
    excerpt_metadata = document.metadata if document.metadata else {}
    return Document(
        type="excerpt",
        parent_document_id=document.id,
        text=excerpt_text,
        keywords=keywords,
        metadata=excerpt_metadata,
        tokens=count_tokens(excerpt_text),
    )


def create_minimap_fn(content: str) -> Callable[[int], str]:
    """
    Given a document with markdown headers, returns a function that outputs the
    current headers for any character position in the document.
    """
    minimap: dict[int, str] = {}
    in_code_block = False
    current_stack = {}
    characters = 0
    for line in content.splitlines():
        characters += len(line)
        if line.startswith("```"):
            in_code_block = not in_code_block
        if in_code_block:
            continue

        if line.startswith("# "):
            current_stack = {1: line}
        elif line.startswith("## "):
            for i in range(2, 6):
                current_stack.pop(i, None)
            current_stack[2] = line
        elif line.startswith("### "):
            for i in range(3, 6):
                current_stack.pop(i, None)
            current_stack[3] = line
        elif line.startswith("#### "):
            for i in range(4, 6):
                current_stack.pop(i, None)
            current_stack[4] = line
        elif line.startswith("##### "):
            for i in range(5, 6):
                current_stack.pop(i, None)
            current_stack[5] = line
        else:
            continue

        minimap[characters - len(line)] = current_stack

    def get_location_fn(n: int) -> str:
        if n < 0:
            raise ValueError("n must be >= 0")
        # get the stack of headers that is closest to - but before - the current
        # position
        stack = minimap.get(max((k for k in minimap if k <= n), default=0), {})

        ordered_stack = [stack.get(i) for i in range(1, 6)]
        return "\n".join([s for s in ordered_stack if s is not None])

    return get_location_fn
