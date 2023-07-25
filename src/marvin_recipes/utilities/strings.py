import re
from functools import lru_cache
from typing import Union

import tiktoken
import xxhash


def tokenize(text: str) -> list[int]:
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo-0613")
    return tokenizer.encode(text)


def detokenize(tokens: list[int]) -> str:
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo-0613")
    return tokenizer.decode(tokens)


def count_tokens(text: str) -> int:
    return len(tokenize(text))


def slice_tokens(text: str, n_tokens: int) -> str:
    tokens = tokenize(text)
    return detokenize(tokens[:n_tokens])


def html_to_content(html: str) -> str:
    import trafilatura

    trafilatura_config = trafilatura.settings.use_config()
    # disable signal, so it can run in a worker thread
    # https://github.com/adbar/trafilatura/issues/202
    trafilatura_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")
    return trafilatura.extract(html, config=trafilatura_config)


def extract_keywords(text: str) -> list[str]:
    import yake

    kw = yake.KeywordExtractor(
        lan="en",
        n=1,
        dedupLim=0.9,
        dedupFunc="seqm",
        windowsSize=1,
        top=10,
        features=None,
    )

    return [k[0] for k in kw.extract_keywords(text)]


def rm_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def rm_text_after(text: str, substring: str) -> str:
    return (
        text[: start + len(substring)]
        if (start := text.find(substring)) != -1
        else text
    )


def split_text(
    text: str,
    chunk_size: int,
    chunk_overlap: float = None,
    last_chunk_threshold: float = None,
    return_index: bool = False,
) -> Union[str, tuple[str, int]]:
    """
    Split a text into a list of strings. Chunks are split by tokens.

    Args:
        text (str): The text to split.
        chunk_size (int): The number of tokens in each chunk.
        chunk_overlap (float): The fraction of overlap between chunks.
        last_chunk_threshold (float): If the last chunk is less than this fraction of
            the chunk_size, it will be added to the prior chunk
        return_index (bool): If True, return a tuple of (chunk, index) where
            index is the character index of the start of the chunk in the original text.
    """
    if chunk_overlap is None:
        chunk_overlap = 0.1
    if chunk_overlap < 0 or chunk_overlap > 1:
        raise ValueError("chunk_overlap must be between 0 and 1")
    if last_chunk_threshold is None:
        last_chunk_threshold = 0.25

    tokens = tokenize(text)

    chunks = []
    for i in range(0, len(tokens), chunk_size - int(chunk_overlap * chunk_size)):
        chunks.append((tokens[i : i + chunk_size], len(detokenize(tokens[:i]))))

    # if the last chunk is too small, merge it with the previous chunk
    if len(chunks) > 1 and len(chunks[-1][0]) < chunk_size * last_chunk_threshold:
        chunks[-2][0].extend(chunks.pop(-1)[0])

    if return_index:
        return [(detokenize(chunk), index) for chunk, index in chunks]
    else:
        return [detokenize(chunk) for chunk, _ in chunks]


@lru_cache(maxsize=2048)
def hash_text(*text: str) -> str:
    bs = [t.encode() if not isinstance(t, bytes) else t for t in text]
    return xxhash.xxh3_128_hexdigest(b"".join(bs))
