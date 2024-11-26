"""helper functions"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import unquote_plus

import orjson
from stac_fastapi.types.rfc3339 import DateTimeType


def is_dict_str_any(var: Any) -> bool:
    """Verify whether the variable is of type dict[str, Any]"""
    if isinstance(var, Dict):
        return all(isinstance(k, str) for k in var.keys())  # type: ignore
    return False


def str2liststr(raw: Any) -> List[str]:
    """Convert str to list[str]"""
    if isinstance(raw, str):
        return raw.split(",")
    return raw


def str2json(k: str, v: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """decoding a URL parameter and then parsing it as JSON."""
    if not v:
        return None
    try:
        return orjson.loads(unquote_plus(v))
    except orjson.JSONDecodeError as e:
        raise Exception(f"{k}: Incorrect JSON object") from e


def format_datetime_range(dt_range: Union[DateTimeType, str]) -> str:
    """
    Convert a datetime object or a tuple of datetime objects to a formatted string for datetime ranges.

    Args:
        dt_range (DateTimeType): The date interval,
            which might be a single datetime or a tuple with one or two datetimes.

    Returns:
        str: A formatted string like 'YYYY-MM-DDTHH:MM:SSZ/..', 'YYYY-MM-DDTHH:MM:SSZ', or the original string input.
    """
    # Handle a single datetime object
    if isinstance(dt_range, datetime):
        return dt_range.isoformat().replace("+00:00", "Z")

    # Handle a tuple containing datetime objects or None
    elif isinstance(dt_range, tuple):
        start, end = dt_range

        # Convert start datetime to string if not None, otherwise use ".."
        start_str = start.isoformat().replace("+00:00", "Z") if start else ".."

        # Convert end datetime to string if not None, otherwise use ".."
        end_str = end.isoformat().replace("+00:00", "Z") if end else ".."

        return f"{start_str}/{end_str}"

    # Return input as-is if it's not any expected type (fallback)
    return dt_range


def dt_range_to_eodag(
    dt_range: Optional[DateTimeType] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Processes a datetime input and returns the start and end times in ISO 8601 format.

    Args:
        dt_range (Optional[DateTimeType]): A single datetime, a tuple of two datetimes, or None.

    Returns:
        Tuple[Optional[str], Optional[str]]: A tuple containing the start and end times in ISO 8601 format,
                                              or (None, None) if the input is None.
    """
    if isinstance(dt_range, tuple):
        start, end = dt_range
    else:
        start = end = dt_range

    start = start.isoformat().replace("+00:00", "Z") if start else None
    end = end.isoformat().replace("+00:00", "Z") if end else None

    return start, end


def extract_cql2_properties(cql2_filter: Dict[str, Any] | str | int) -> Dict[str, str | int]:
    """Extract CQL2 properties from the full CQL2 filter json recursively.

    >>> cql2_filter = {
            'op': 'and',
            'args': [
                {
                    'op': 'and',
                    'args': [
                        {
                            'op': '=',
                            'args': [
                                {'property': 'id'},
                                'S2B_MSIL1C_20180212T104139_N0500_R008_T31TEJ_20230810T140400'
                            ]
                        },
                        {
                            'op': '=',
                            'args': [
                                {'property': 'collection'},
                                'SENTINEL-2'
                            ]
                        }
                    ]
                },
                {
                    'op': '=',
                    'args': [
                        {'property': 'cloudCover'},
                        10
                    ]
                }
            ]
        }
    >>> cql2_filter_properties = extract_cql2_properties(cql2_filter)
    >>> cql2_filter_properties
    {'id': 'S2B_MSIL1C_20180212T104139_N0500_R008_T31TEJ_20230810T140400', 'collection': 'SENTINEL-2', 'cloudCover': 10}

    :param cql2_filter: the full CQL2 filter json or a part of it during the recursivity process
    :returns: a dictionnary containing (property_name: property_value) pairs
    """
    cql2_filter_properties = {}

    # ensure we are dealing with a dictionary that has an "args" key
    if isinstance(cql2_filter, dict):
        for item in cql2_filter.get("args", []):
            # if the item is a dictionary, process it
            if isinstance(item, dict):
                # if the item contains a "property" key, extract it to get the property name
                # create a pair with its matching value given in the second element of its parent list
                if "property" in item and len(cql2_filter["args"]) == 2:
                    cql2_filter_properties[item["property"]] = cql2_filter["args"][1]

                # recursively call the function to process nested dictionaries
                cql2_filter_properties.update(extract_cql2_properties(item))

    return cql2_filter_properties
