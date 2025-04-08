import functools
import json
import sys
import traceback


def process_error(func):
    """Decorator to handle and process errors uniformly"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log the error type and message for better debugging
            print(
                f"Error in {func.__name__}: {type(e).__name__} - {str(e)}\n"
                f"{traceback.format_exc()}",
                file=sys.stderr,
            )
            # Convert the error to a more informative message
            error_dict = {
                "error": True,
                "message": str(e),
                "code": getattr(e, "error_code", 500),
                "traceback": getattr(e, "error_traceback", ""),
            }
            return json.dumps(error_dict)

    return wrapper
