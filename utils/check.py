from functools import wraps

from utils.logger import logger


def checkvars(varlist, errorinfo):
    """
    Decorator to check if variables are defined before running a function.
    """
    if isinstance(varlist, str):
        varlist = [varlist]

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            exist_status = [self._is_defined(var) for var in varlist]
            assert not any(status is False for status in exist_status), errorinfo
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def infomanage(successinfo=None, errorinfo=None):
    """
    Decorator to log information at different stages of function execution.
    """

    def decorator(func):
        nonlocal successinfo, errorinfo
        successinfo = successinfo or f"Successfully called function {func.__name__}"
        errorinfo = errorinfo or f"Failed to call function {func.__name__}"

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                result = func(self, *args, **kwargs)
                logger.info(successinfo)
                return result
            except Exception:
                logger.error(errorinfo)
                raise

        return wrapper

    return decorator
