from prefect import flow, task
from prefect.filesystems import GCS
from prefect.results import PersistedResult

STORAGE = GCS.load("marvin-result-storage")
SERIALIZER = "json"
STORAGE_KEY = "foo.json"


@task(
    result_serializer=SERIALIZER,
    result_storage_key=STORAGE_KEY,
)
def add(x, y):
    return x + y


@flow(result_storage=STORAGE)
def my_flow():
    return add(1, 2)


if __name__ == "__main__":
    local_result = my_flow()

    result_ref = PersistedResult(
        storage_block_id=STORAGE._block_document_id,
        serializer_type=SERIALIZER,
        storage_key=STORAGE_KEY,
    )

    assert local_result == result_ref.get() == 3
