"""helper functions"""

from typing import List, Union


def str2liststr(raw: Union[str, List[str]]) -> List[str]:
    """Convert str to list[str]"""
    if isinstance(raw, list):
        return raw
    return raw.split(",")
