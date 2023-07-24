import uuid
from functools import lru_cache

from pydantic import constr

# UUID regex
UUID_REGEX = r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
# specific prefix
PREFIXED_UUID_REGEX = r"\b{prefix}_[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}\b"  # noqa E501


@lru_cache()
def get_id_type(prefix: str = None) -> type:
    if prefix is None:
        type_ = constr(regex=UUID_REGEX)
        type_.new = lambda: str(uuid.uuid4())
    else:
        if "_" in prefix:
            raise ValueError("Prefix must not contain underscores.")
        type_ = constr(regex=PREFIXED_UUID_REGEX.format(prefix=prefix))
        type_.new = lambda: f"{prefix}_{uuid.uuid4()}"
    return type_


DocumentID = get_id_type(prefix="doc")
MessageID = get_id_type(prefix="msg")
