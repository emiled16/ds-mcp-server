from typing import Callable, Optional


def ignore_errors(func: Callable) -> Optional[Callable]:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error occurred in experiment: {e}")
            # Optionally, log the error or take other actions
            return None  # Return None or any other value that indicates failure

    return wrapper
