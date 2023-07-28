import inspect
from contextlib import ContextDecorator
from functools import wraps
from typing import Callable, Type, TypeVar

from marvin.engine.language_models import ChatLLM
from prefect import Flow, flow
from prefect import tags as prefect_tags

T = TypeVar("T")


async def record_usage(ai_app_result: dict):
    llm_response = ai_app_result.get("llm_response", {})
    usage = llm_response.get("usage", {})
    # replace with your own usage tracking
    print(f"||TOKEN USAGE|| {' | '.join(f'{k}: {v}' for k, v in usage.items())}")


def prefect_wrapped_function(
    func: Callable[..., T],
    decorator: Callable[..., Callable[..., T]] = flow,
    tags: set | None = None,
    flow_kwargs: dict | None = None,
) -> Callable[..., Flow]:
    """Decorator for wrapping a function with a prefect decorator."""
    tags = tags or set()

    @wraps(func)
    async def wrapper(*args, **kwargs):
        if (settings := flow_kwargs) is None:
            settings = {
                "validate_parameters": False,
                "flow_run_name": "call {self.name}",
            }
        wrapped_callable = decorator(**settings)(func)
        with prefect_tags(*tags):
            result = wrapped_callable(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result

            await record_usage(result.dict())
            return result

    return wrapper


class WatchLLM(ContextDecorator):
    """Context decorator for patching a method with a prefect flow."""

    def __init__(
        self,
        patch_cls: Type = ChatLLM,
        patch_method_name: str = "run",
        tags: set | None = None,
        flow_kwargs: dict | None = None,
    ):
        """Initialize the context manager.
        Args:
            tags: Prefect tags to apply to the flow.
            flow_kwargs: Keyword arguments to pass to the flow.
        """
        self.patch_cls = patch_cls
        self.patch_method = patch_method_name
        self.tags = tags
        self.flow_kwargs = flow_kwargs

    def __enter__(self):
        """Called when entering the context manager."""
        self.patched_methods = []
        for cls in {self.patch_cls, *self.patch_cls.__subclasses__()}:
            self._patch_method(
                cls=cls,
                method_name=self.patch_method,
                decorator=prefect_wrapped_function,
            )

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Reset methods when exiting the context manager."""
        for cls, method_name, original_method in self.patched_methods:
            setattr(cls, method_name, original_method)

    def _patch_method(self, cls, method_name, decorator):
        """Patch a method on a class with a decorator."""
        original_method = getattr(cls, method_name)
        modified_method = decorator(
            original_method, tags=self.tags, flow_kwargs=self.flow_kwargs
        )
        setattr(cls, method_name, modified_method)
        self.patched_methods.append((cls, method_name, original_method))


if __name__ == "__main__":
    import warnings  # I know, I know, later

    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        message=".*was excluded from schema since JSON schema has no equivalent type.*",
    )
    import asyncio

    from marvin import AIApplication

    todo = AIApplication(
        name="todo",
        description="A todo tracker.",
        plan_enabled=False,
    )

    @flow(log_prints=True)
    async def interact(message: str) -> str:
        """Interact with the user."""
        with WatchLLM():
            response = await todo.run(input_text=message)
            print(response.content)

    asyncio.run(interact("I need to buy milk."))
