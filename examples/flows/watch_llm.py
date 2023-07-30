import asyncio
import importlib
import inspect
import warnings
from contextlib import ContextDecorator
from functools import wraps
from typing import Callable, Optional, TypeVar

from marvin import AIApplication
from prefect import Flow, flow
from prefect import tags as prefect_tags
from pydantic import BaseModel, PrivateAttr

warnings.filterwarnings(  # I know, I know, later
    "ignore",
    category=UserWarning,
    message=".*JSON schema has no equivalent type.*",
)

T = TypeVar("T")

DEFAULT_FLOW_SETTINGS = {"validate_parameters": False, "flow_run_name": "{self.name}"}


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
        settings = {**(flow_kwargs or {}), **DEFAULT_FLOW_SETTINGS}
        with prefect_tags(*tags):
            result = decorator(func, **settings)(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result

            await record_usage(result.dict())
            return result

    return wrapper


class WatchLLM(BaseModel, ContextDecorator):
    """Context decorator for patching a method with a prefect flow."""

    patch_cls: str = "marvin.engine.language_models.ChatLLM"
    patch_method_name: str = "run"
    patch_decorator: Callable = prefect_wrapped_function
    tags: Optional[set] = None
    flow_kwargs: Optional[dict] = None
    _patched_methods: list[tuple[type, str, Callable]] = PrivateAttr(
        default_factory=list
    )

    def __enter__(self):
        """Called when entering the context manager."""
        module_name, class_name = self.patch_cls.rsplit(".", 1)
        module = importlib.import_module(module_name)
        patch_cls = getattr(module, class_name)

        for cls in {patch_cls, *patch_cls.__subclasses__()}:
            self._patch_method(
                cls=cls,
                method_name=self.patch_method_name,
                decorator=self.patch_decorator,
            )

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Reset methods when exiting the context manager."""
        for cls, method_name, original_method in self._patched_methods:
            setattr(cls, method_name, original_method)

    def _patch_method(self, cls, method_name, decorator):
        """Patch a method on a class with a decorator."""
        original_method = getattr(cls, method_name)
        modified_method = decorator(
            original_method, tags=self.tags, flow_kwargs=self.flow_kwargs
        )
        setattr(cls, method_name, modified_method)
        self._patched_methods.append((cls, method_name, original_method))


####################################################################################################
# Example usage in a wrapping (but not necessary) parent flow

if __name__ == "__main__":
    todo = AIApplication(
        name="todo",
        description="A todo tracker.",
        plan_enabled=False,
    )

    @flow(log_prints=True)
    async def interact(message: str) -> str:
        """Interact with the user."""
        with WatchLLM(tags={"ai-todo-app"}):
            response = await todo.run(input_text=message)
            print(response.content)

    asyncio.run(interact("I need to buy milk."))
