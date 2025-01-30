"""Generate a CloudFormation VPC resource."""

from typing import Any, Callable, TypedDict, get_type_hints

from troposphere import constants
import troposphere.ec2

from cfnlite.lib import tags, utils, validators


# Callbacks type, just to sure things up for people with cool IDEs
class CallBacks(TypedDict):
    """Types for each of the callback function signatures."""

    add_symbol: Callable[[str, Any], None]
    get_symbol: Callable[[str], Any]
    add_resource: Callable[[Any], None]


# details: (
#     https://docs.aws.amazon.com/ \
#     AWSCloudFormation/latest/UserGuide/aws-resource-ec2-vpc.html
# )
class VPC(TypedDict, total=False):
    """VPC properties."""

    CidrBlock: str
    EnableDnsHostnames: bool
    EnableDnsSupport: bool
    InstanceTenancy: str
    Ipv4IpamPoolId: str
    Ipv4NetmaskLength: int
    Tags: list[dict[str, str]]


EXPECTS_LIST: set[str] = set("Tags")

VPC_DEFAULTS: set[str] = {"cidrblock"}


def _default_vpc_params() -> VPC:
    """VPC property attributes.

    :returns: A dict containing all the CFN VPC resource attributes
        Users can overwrite any of these values.
    :rtype: VPC
    """
    defaults: VPC = {
        "CidrBlock": constants.VPC_CIDR_16,
        "EnableDnsHostnames": False,
        "EnableDnsSupport": False,
        "InstanceTenancy": "default",
        "Ipv4IpamPoolId": "",
        "Ipv4NetmaskLength": "",
        "Tags": [],
    }

    defaults.update(utils.resource_attributes())
    return defaults


def build(name, callbacks, vpc_properties):
    """Build a VPC resource from a cnflite file.

    :param str name: the cfn name of the resource
    :param CallBacks callbacks: object containing callbacks
    :param dict vpc_properties: VPC properties read in from a cnflite
        file.
    :raises ValueError: if there is an invalid property.
    """
    # holds the final set of correctly formatted VPC properties to pass into
    # the cfn generator
    vpc: VPC = _default_vpc_params()
    lang: list[str] = utils.create_lang(vpc.keys())

    # Allow users to overwrite any default value but protect against them
    # naming the same value twice in the cnflite file. This is easily done
    # by naming the same property twice but using different casee i.e.
    # upper/lower for each version of the property.
    # Without this its last entry wins, which isn't necessarily a bad solution
    # but it does seem unintuitive from a user prospective.
    resource_tracker: set[str] = set()
    for key, value in vpc_properties.items():
        if key.lower() in resource_tracker:
            raise ValueError(
                f"Each property can only be used once. Offending prop: {key}")
        try:
            # this function returns a generic ValueError, so we want to catch
            # it here and propagate it with the correct error message.
            cleaned_property_name: str = validators.validate_props(
                key, value, vpc, lang, EXPECTS_LIST)

        except ValueError as err:
            msg: str = f"{key} is an invalid attribute for VPC's."
            raise ValueError(msg) from err

        if cleaned_property_name.lower() == "tags":
            formatted_tags = tags.add_tags(
                name, value, callbacks["get_symbol"])
            utils.nested_update(vpc, "Tags", formatted_tags)

        # handle any refs
        validators.resolve_refs(
            cleaned_property_name, vpc, callbacks["get_symbol"])

        resource_tracker.add(key.lower())

    cleaned_vpc: VPC = utils.clean(vpc, resource_tracker.union(VPC_DEFAULTS))
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
