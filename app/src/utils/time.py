from collections.abc import Callable
from functools import wraps
from logging import getLogger
from time import time
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def timing(f: Callable[P, T]) -> Callable[P, T]:
    @wraps(f)
    def wrap(*args: P.args, **kw: P.kwargs) -> T:
        logger = getLogger(f.__module__)
        ts = time()
        result = f(*args, **kw)
        te = time()
        logger.info(f"func:{f.__name__} args:[{args}, {kw}] took: {te - ts:.4f} sec")
        return result

    return wrap
