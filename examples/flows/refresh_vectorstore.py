from datetime import timedelta

from marvin_recipes.documents import Document
from marvin_recipes.loaders.base import Loader
from marvin_recipes.loaders.discourse import DiscourseLoader
from marvin_recipes.loaders.github import GitHubRepoLoader
from marvin_recipes.loaders.web import HTMLLoader, SitemapLoader
from marvin_recipes.vectorstores.chroma import Chroma
from prefect import flow, task
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
    SitemapLoader(
        urls=["https://docs.prefect.io/sitemap.xml"],
        exclude=["api-ref"],
    ),
    # OpenAPISpecLoader(openapi_spec_url="https://api.prefect.cloud/api/openapi.json"),
    HTMLLoader(
        urls=[
            "https://prefect.io/company",
            "https://prefect.io/security",
        ],
    ),
    GitHubRepoLoader(
        repo="prefecthq/prefect",
        include_globs=["flows/**", "README.md", "RELEASE-NOTES.md"],
        exclude_globs=[
            "tests/**/*",
            "docs/**/*",
            "**/migrations/**/*",
            "**/__init__.py",
            "**/_version.py",
        ],
    ),
    DiscourseLoader(
        url="https://discourse.prefect.io",
        n_topic=100,
        include_topic_filter=include_topic_filter,
    ),
    GitHubRepoLoader(
        repo="prefecthq/prefect-recipes",
        include_globs=[
            "flows-advanced/**/*.py",
            "README.md",
            "flows-starter/*.py",
        ],
    ),
]


@task(
    retries=2,
    retry_delay_seconds=[3, 60],
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1),
    task_run_name="Run {loader.__class__.__name__}",
    persist_result=True,
    # refresh_cache=True,
)
async def run_loader(loader: Loader) -> list[Document]:
    return await loader.load()


@flow(
    name="Update Marvin's Knowledge",
    log_prints=True,
    # result_storage=GCS.load("marvin-result-storage"),
)
async def update_marvin_knowledge(
    collection_name: str = "marvin",
    wipe_collection: bool = True,
    chroma_client_type: str = "base",
):
    """Flow updating Marvin's knowledge with info from the Prefect community."""

    documents = [
        doc
        for future in await run_loader.map(quote(prefect_loaders))
        for doc in await future.result()
    ]

    async with Chroma(
        collection_name=collection_name, client_type=chroma_client_type
    ) as chroma:
        if wipe_collection:
            await chroma.reset_collection()
        n_docs = await chroma.add(documents)

        print(f"Added {n_docs} documents to the {collection_name} collection.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(
        update_marvin_knowledge(collection_name="marvin", chroma_client_type="http")
    )
