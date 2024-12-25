"""Validate incoming CFNLite props."""

from typing import Any, Callable, TypeVar

import troposphere

from cfnlite.lib import utils

# function signature for getting a symbol from symbol table
GetSymbolCallable = Callable[[str], Any]
T = TypeVar("T")


def _handle_refs(
    prop: str,
    symbol_callback: Callable[[str], Any],
) -> troposphere.Ref:
    """Handle generating a cfn Ref.

    :param str prop: the resource property name to reference
    :param Callable[[str], Any] symbol_callback: callback function to grab the
        reference from an external symbol table. The resource name is the
        index into the symbol table.

    :returns: the reference object
    :rtype: troposphere.Ref
    :raises ValueError: if ref keyword is formatted incorrectly
    """
    value: list[str] = prop.split()

    if len(value) < 2 or len(value) > 2:
        raise ValueError(
            "Keyword 'ref' must be followed by exactly one argument")

    return troposphere.Ref(symbol_callback(value[1]))


def _check_list_for_refs(
    prop_list: list[str],
    callback: Callable[[str], Any],
) -> list[str, troposphere.Ref]:
    """Check a list of props for any references to other resources.

    :param list[str] prop_list: list of props
    :param Callable[[str], Any] callback: callback function to handle
        resolving references.
    :returns: a list of resolved references (if needed)
    :rtype: list[str, troposphere.Ref]
    """
    for idx, item in enumerate(prop_list):
        if isinstance(item, str) and item.strip().startswith("ref"):
            prop_list[idx] = _handle_refs(item, callback)

    return prop_list


def resolve_refs(
    prop_name: str,
    props: T,
    expects_list: set[str],
    callback: Callable[[str], Any],
) -> None:
    """Resolve any references the property needs.

    :param str prop_name: the property name
    :param T props: object holding final set of correctly formatted props
        passed down to the resource generator
    :param Callable callback: callback to help resolve references
    """
    # get the value associated with the property name
    value: Any = utils.nested_find(props, prop_name)

    if value is None:
        raise ValueError(f"Unable to find key: {prop_name}")

    if prop_name in expects_list:
        handled_refs = _check_list_for_refs(value, callback)
        utils.nested_update(props, prop_name, handled_refs)

    elif (isinstance(value, str) and value.strip().startswith("ref")):
        handled_refs = _handle_refs(value, callback)
        utils.nested_update(props, prop_name, handled_refs)


def validate_props(
    key: str,
    value: str | list[str],
    props: T,
    lang: list[str],
    expects_list: set[str],
) -> str:
    """Validate incoming resource properties.

    :param str key: the property name
    :param list[str] value: the property value(s)
    :param T props: object holding final set of correctly formatted props
        passed down to the resource generator
    :param list[str] lang: the property options for a given resource
    :param set[str] expects_list: properties that expect lists as values.
        This is to allow users to define single item lists as just the a string
        containing the value.

    :returns: correctly formatted property name
    :rtype: str
    :raises ValueError: if key is an invalid EC2 property
    """
    # This ensures our prop name gets correctly formatted e.g.:
    # securitygroups -> SecurityGroups
    cleaned_param: list[str] = utils.property_validator(key, lang)
    if not cleaned_param:
        raise ValueError

    validated_param: str = "".join(cleaned_param)

    if validated_param in expects_list and isinstance(value, str):
        value = [value]

    utils.nested_update(props, validated_param, value)

    return validated_param
