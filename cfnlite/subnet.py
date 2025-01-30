"""Generate a subnet from CFNLite."""

from typing import Any, Callable, TypedDict, get_type_hints

from troposphere import Ref
import troposphere.ec2

from cfnlite.lib import tags, utils, validators

TagType = dict[str, str | Ref]


# Callbacks type, just to sure things up for people with cool IDEs
class CallBacks(TypedDict):
    """Types for each of the callback function signatures."""

    add_symbol: Callable[[str, Any], None]
    get_symbol: Callable[[str], Any]
    add_resource: Callable[[Any], None]


# details: (
#     https://docs.aws.amazon.com/ \
#     AWSCloudFormation/latest/UserGuide/aws-resource-ec2-subnet.html
# )
class Subnet(TypedDict, total=False):
    """Subnet attributes currently supported."""

    AssignIpv6AddressOnCreation: bool
    AvailabilityZone: str
    AvailabilityZoneId: str
    CidrBlock: str
    EnableDns64: bool
    EnableLniAtDeviceIndex: int
    Ipv4IpamPoolId: str
    Ipv4NetmaskLength: int
    Ipv6CidrBlock: str
    Ipv6IpamPoolId: str
    Ipv6Native: bool
    Ipv6NetmaskLength: int
    MapPublicIpOnLaunch: bool
    OutpostArn: str
    Tags: list[TagType]
    VpcId: str


EXPECTS_LIST = set("Tags")

SUBNET_DEFAULTS = {"availabilityzone", "cidrblock", "vpcid"}


def _default_subnet_params() -> Subnet:
    """Subnet property attributes.

    :returns: A dict containing all the CFN Subnet resource attributes
        Users can overwrite any of these values.
    :rtype: Subnet
    """
    defaults: dict[str, bool | list | str] = {
        "AssignIpv6AddressOnCreation": False,
        "AvailabilityZone": "eu-west-2a",
        "AvailabilityZoneId": "",
        "CidrBlock": "10.0.1.0/24",
        "EnableDns64": "",
        "EnableLniAtDeviceIndex": "",
        "Ipv4IpamPoolId": "",
        "Ipv4NetmaskLength": "",
        "Ipv6CidrBlock": "",
        "Ipv6IpamPoolId": "",
        "Ipv6Native": "",
        "Ipv6NetmaskLength": "",
        "MapPublicIpOnLaunch": "",
        "OutpostArn": "",
        "PrivateDnsNameOptionsOnLaunch": "",
        "Tags": "",
        "VpcId": "fake-vpc-id",
    }

    defaults.update(utils.resource_attributes())
    return defaults


def _subnet_to_nacl(name: str, callbacks: CallBacks) -> None:
    """Subnet to NACL connection.

    :param str name: name of parent resource
    :param CallBacks callbacks: object containing callbacks
    """
    sub_to_nacl_resource: dict[str, Ref] = {
        "NetworkAclId": Ref(callbacks["get_symbol"]("networkacl")),
        "SubnetId": Ref(callbacks["get_symbol"]("subnet")),
    }

    callbacks["add_resource"](
        troposphere.ec2.SubnetNetworkAclAssociation(
            f"{name}SubnetToNACL", **sub_to_nacl_resource))


def _subnet_to_route_table(name: str, callbacks: CallBacks) -> None:
    """Subnet to RouteTable connection.

    :param str name: name of parent resource
    :param CallBacks callbacks: object containing callbacks
    """
    sub_to_rt_resource: dict[str, Ref] = {
        "RouteTableId": Ref(callbacks["get_symbol"]("routetable")),
        "SubnetId": Ref(callbacks["get_symbol"]("subnet")),
    }

    callbacks["add_resource"](
        troposphere.ec2.SubnetRouteTableAssociation(
            f"{name}SubnetToRouteTable", **sub_to_rt_resource))


def build(
    name: str,
    callbacks: CallBacks,
    subnet_props: dict[str, Any],
) -> None:
    """Build a cfn Subnet resource.

    :param str name: the cfn name of the resource
    :param CallBacks callbacks: object containing callbacks
    :param dict subnet_props: Subnet properties read in from a cnflite
        file.
    :raises ValueError: if there is an invalid property.
    """
    # holds the final set of correctly formatted Subnet properties to pass into
    # the cfn generator
    subnet: Subnet = _default_subnet_params()

    lang: list[str] = utils.create_lang(subnet.keys())

    # Allow users to overwrite any default value but protect against them
    # naming the same value twice in the cnflite file. This is easily done
    # by naming the same property twice but using different casee i.e.
    # upper/lower for each version of the property.
    # Without this its last entry wins, which isn't necessarily a bad solution
    # but it does seem unintuitive from a user prospective.
    resource_tracker = set()
    for key, value in subnet_props.items():
        if key.lower() in resource_tracker:
            raise ValueError(
                f"Each property can only be used once. Offending prop: {key}")

        try:
            # this function returns a generic ValueError, so we want to catch
            # it here and propagate it with the correct error message.
            cleaned_property_name: str = validators.validate_props(
                key, value, subnet, lang, EXPECTS_LIST)

        except ValueError as err:
            msg: str = f"{key} is an invalid attribute for Subnet."
            raise ValueError(msg) from err

        if key.lower() == "tags":
            formatted_tags = tags.add_tags(
                name, value, callbacks["get_symbol"])
            utils.nested_update(subnet, "Tags", formatted_tags)

        # handle any refs
        validators.resolve_refs(
            cleaned_property_name, subnet, callbacks["get_symbol"])

        resource_tracker.add(key.lower())

    cleaned_subnet: dict[str, Any] = utils.clean(
        subnet, resource_tracker.union(SUBNET_DEFAULTS))
    new_subnet = troposphere.ec2.Subnet(name, **cleaned_subnet)

    # add subnet to template
    callbacks["add_resource"](new_subnet)
    # add subnet to symbol table
    callbacks["add_symbol"]("subnet", new_subnet)

    # we have to try each of these separately so if any lookup errors
    # the others will still be checked
    sym_func: tuple[str, Callable[[str, CallBacks], None]] = [
        ("networkacl", _subnet_to_nacl),
        ("routetable", _subnet_to_route_table)
    ]
    for symbol, function in sym_func:
        try:
            callbacks["get_symbol"](symbol)
            function(name, callbacks)

        except KeyError:
            pass


def explain():
    """List the current supported Subnet properties."""
    # we'll import pprint here as its not that heavily used
    import pprint  # pylint: disable=import-outside-toplevel

    # we can use the typed dict to get this data
    pprint.pprint(get_type_hints(Subnet))
