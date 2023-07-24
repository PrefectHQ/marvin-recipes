import re
from datetime import timedelta

import marvin
from marvin.loaders.base import Loader
from marvin.loaders.web import SitemapLoader
from marvin.utilities.documents import Document
from marvin.vectorstores.chroma import Chroma
from prefect import flow, task
from prefect.blocks.core import Block
from prefect.filesystems import GCS
from prefect.tasks import task_input_hash
from prefect.utilities.annotations import quote

# Discourse categories
SHOW_AND_TELL_CATEGORY_ID = 26
HELP_CATEGORY_ID = 27

PREFECT_COMMUNITY_CATEGORIES = {
    SHOW_AND_TELL_CATEGORY_ID,
    HELP_CATEGORY_ID,
}


def include_topic_filter(topic) -> bool:
    return (
        "marvin" in topic["tags"]
        and topic["category_id"] in PREFECT_COMMUNITY_CATEGORIES
    )


prefect_loaders = [
    # SitemapLoader(
    #     urls=["https://docs.prefect.io/sitemap.xml"],
    #     exclude=["api-ref"],
    # ),
    # OpenAPISpecLoader(
    #     openapi_spec_url="https://api.prefect.cloud/api/openapi.json",
    #     api_doc_url="https://app.prefect.cloud/api",
    # ),
    # HTMLLoader(
    #     urls=[
    #         "https://prefect.io/about/company/",
    #         "https://prefect.io/security/overview/",
    #         "https://prefect.io/security/sub-processors/",
    #         "https://prefect.io/security/gdpr-compliance/",
    #         "https://prefect.io/security/bug-bounty-program/",
    #     ],
    # ),
    # GitHubRepoLoader(
    #     repo="prefecthq/prefect",
    #     include_globs=["flows/**", "README.md", "RELEASE-NOTES.md"],
    #     exclude_globs=[
    #         "tests/**/*",
    #         "docs/**/*",
    #         "**/migrations/**/*",
    #         "**/__init__.py",
    #         "**/_version.py",
    #     ],
    # ),
    # DiscourseLoader(
    #     url="https://discourse.prefect.io",
    #     n_topic=300,
    #     include_topic_filter=include_topic_filter,
    # ),
    # GitHubRepoLoader(
    #     repo="prefecthq/prefect-recipes",
    #     include_globs=["flows-advanced/**/*.py", "README.md"],
    # ),
    SitemapLoader(
        urls=["https://www.prefect.io/sitemap.xml"],
        include=[re.compile("prefect.io/guide/case-studies/.+")],
    ),
]


async def set_chroma_settings():
    """
    the `json/chroma-client-settings` Block should look like this:
    {
        "chroma_server_host": "<chroma server IP address>",
        "chroma_server_http_port": <chroma server port>
    }
    """
    chroma_client_settings = await Block.load("json/chroma-client-settings")

    for key, value in chroma_client_settings.value.items():
        setattr(marvin.settings, key, value)


def html_parser_fn(html: str) -> str:
    import trafilatura

    trafilatura_config = trafilatura.settings.use_config()
    # disable signal, so it can run in a worker thread
    # https://github.com/adbar/trafilatura/issues/202
    trafilatura_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")
    return trafilatura.extract(html, config=trafilatura_config)


def keyword_extraction_fn(text: str) -> list[str]:
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


@task(
    retries=2,
    retry_delay_seconds=[3, 60],
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1),
    task_run_name="Run {loader.__class__.__name__}",
    persist_result=True,
)
async def run_loader(loader: Loader) -> list[Document]:
    return await loader.load()


@flow(
    name="Update Marvin's Knowledge",
    log_prints=True,
    result_storage=GCS.load("marvin-result-storage"),
)
async def update_marvin_knowledge(
    collection_name: str = "marvin",
    wipe_collection: bool = True,
):
    """Flow updating Marvin's knowledge with info from the Prefect community."""
    # forward_logger_to_prefect(get_marvin_logger())

    marvin.settings.html_parsing_fn = html_parser_fn
    marvin.settings.keyword_extraction_fn = keyword_extraction_fn

    documents = [
        doc
        for future in await run_loader.map(quote(prefect_loaders))
        for doc in await future.result()
    ]

    async with Chroma(collection_name) as chroma:
        if wipe_collection:
            await chroma.delete()
        n_docs = await chroma.add(documents)

        print(f"Added {n_docs} documents to the {collection_name} collection.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(update_marvin_knowledge("prefect", wipe_collection=False))
