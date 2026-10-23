"""Bounded reuse of literal parsing across draft analyses; never execute source."""
import ast
import copy
from functools import lru_cache


@lru_cache(maxsize=4096)
def _parse(text):
    try:
        return True, ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return False, None


def literal_eval(text):
    if not isinstance(text, str) or len(text) > 8192:
        return ast.literal_eval(text)
    valid, value = _parse(text)
    if not valid:
        raise ValueError('不是静态字面量。')
    return value if isinstance(value, (str, int, float, bool, type(None))) else copy.deepcopy(value)
