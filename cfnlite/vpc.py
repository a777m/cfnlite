"""Generate a CloudFormation VPC resource."""

from typing import Any, Callable, TypedDict, get_type_hints

from troposphere import Ref, constants
import troposphere.ec2

from cfnlite.lib import utils


# Callbacks type, just to sure things up for people with cool IDEs
class CallBacks(TypedDict):
    """Types for each of the callback function signatures."""

    add_symbol: Callable[[str, Any], None]
    get_symbol: Callable[[str], Any]
    add_resource: Callable[[Any], None]


class VPC(TypedDict, total=False):
    """VPC properties."""

    CidrBlock: str
    EnableDnsHostnames: bool
    EnableDnsSupport: bool
    InstanceTenancy: str
    Ipv4IpamPoolId: str
    Ipv4NetmaskLength: int


EXPECTS_LIST: set[str] = set()


LANG: list[str] = [
    "Block", "Cidr", "Dns", "Enable", "Hostnames", "Id", "Instance",
    "Ipv4", "Ipam", "Length", "Netmask", "Pool", "Support", "Tenancy",
]


VPC_DEFAULTS: set[str] = {"cidrblock"}


def _default_vpc_params() -> VPC:

    defaults: VPC = {
        "CidrBlock": constants.VPC_CIDR_16,
        "EnableDnsHostnames": False,
        "EnableDnsSupport": False,
        "InstanceTenancy": "default",
        "Ipv4IpamPoolId": "",
        "Ipv4NetmaskLength": "",
    }

    defaults.update(utils.resource_attributes())
    return defaults


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

    return Ref(symbol_callback(value[1]))


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
    props: VPC,
    callback: Callable[[str], Any]
) -> None:
    """Resolve any references the property needs.

    :param str prop_name: the property name
    :param EC2 props: object holding final set of correctly formatted props
        passed down to the resource generator
    :param Callable callback: callback to help resolve references
    """
    # get the value associated with the property name
    value: Any = utils.nested_find(props, prop_name)

    if not value:
        raise ValueError(f"Unable to find key: {prop_name}")

    if prop_name in EXPECTS_LIST:
        handled_refs = _check_list_for_refs(value, callback)
        utils.nested_update(props, prop_name, handled_refs)

    elif (isinstance(value, str) and value.strip().startswith("ref")):
        handled_refs = _handle_refs(value, callback)
        utils.nested_update(props, prop_name, handled_refs)


def _validate_props(
    key: str,
    value: str | list[str],
    props: VPC,
) -> str:
    """Validate incoming resource properties.

    :param str key: the property name
    :param str | list[str] value: the property value(s)
    :param EC2 props: object holding final set of correctly formatted props
        passed down to the resource generator

    :returns: correctly formatted property name
    :rtype: str
    :raises ValueError: if key is an invalid EC2 property
    """
    # This ensures our prop name gets correctly formatted e.g.:
    # securitygroups -> SecurityGroups
    cleaned_param: list[str] = utils.property_validator(key, LANG)
    if not cleaned_param:
        raise ValueError(f"{key} is an invalid attribute for EC2's.")

    validated_param: str = "".join(cleaned_param)

    if validated_param in EXPECTS_LIST and isinstance(value, str):
        value = [value]

    utils.nested_update(props, validated_param, value)

    return validated_param


def build(name, callbacks, vpc_properties):
    vpc = _default_vpc_params()

    resource_tracker = set()

    for key, value in vpc_properties.items():
        if key.lower() in resource_tracker:
            raise ValueError(
                f"Each property can only be used once. Offending prop: {key}")

        cleaned_property_name = _validate_props(key, value, vpc)
        # handle any refs
        resolve_refs(cleaned_property_name, vpc, callbacks["get_symbol"])

        resource_tracker.add(key.lower())


    cleaned_vpc = utils.clean(vpc, resource_tracker.union(VPC_DEFAULTS))
    new_vpc = troposphere.ec2.VPC(name, **cleaned_vpc)

    # add vpc to template
    callbacks["add_resource"](new_vpc)
    # add vpc to symbol table
    callbacks["add_symbol"]("vpc", new_vpc)


def explain():
    """List the current supported VPC properties."""
    # we'll import pprint here as its not that heavily used
    import pprint  # pylint: disable=import-outside-toplevel

    # we can use the typed dict to get this data
    pprint.pprint(get_type_hints(VPC))
