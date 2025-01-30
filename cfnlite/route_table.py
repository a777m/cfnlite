"""Generate a RouteTable from CFNLite."""

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
#     AWSCloudFormation/latest/UserGuide/aws-resource-ec2-routetable.html
# )
class RouteTable(TypedDict):
    """Protocol for Route Tables."""

    Tags: list[TagType]
    VpcId: str


EXPECTS_LIST = set("Tags")

# required fields
ROUTE_TABLE_DEFAULTS = {"vpcid"}


def _route_to_igw(name: str, callbacks: CallBacks) -> None:
    """Route table -> internet gateway route.

    :param str name: cfn name of the parent resource
    :param CallBacks callbacks: object with callbacks
    """
    route: dict[str, Ref] = {
        "DestinationCidrBlock": "0.0.0.0/0",
        "GatewayId": Ref(callbacks["get_symbol"]("internetgateway")),
        "RouteTableId": Ref(callbacks["get_symbol"]("routetable")),
    }

    route = troposphere.ec2.Route(f"{name}RouteToIGW", **route)
    callbacks["add_resource"](route)


def _default_route_table_params() -> RouteTable:
    """RouteTable parameters with sensible defaults.

    :returns: A dict containing CFN parameters for route tables
    :rtype: RouteTable
    """
    defaults: dict[str, str | list[TagType]] = {
        "Tags": [],
        "VpcId": "id-example-vpc",
    }

    defaults.update(utils.resource_attributes())
    return defaults


def build(
    name: str,
    callbacks: CallBacks,
    route_table_properties: dict[str, str | list[TagType]],
) -> None:
    """Generate a CFN RouteTable resource.

    :param str name: the cfn name for the resource
    :param CallBacks callbacks: object containing callbacks
    :param dict route_table_properties: RT props read in from a cfnlit file.

    :raises ValueError: if there is an invalid property.
    """
    # holds the final set of correctly formatted RT properties to pass into
    # the cfn generator
    route_table = _default_route_table_params()

    lang: list[str] = utils.create_lang(route_table.keys())

    # Allow users to overwrite any default value but protect against them
    # naming the same value twice in the cnflite file. This is easily done
    # by naming the same property twice but using different casee i.e.
    # upper/lower for each version of the property.
    # Without this its last entry wins, which isn't necessarily a bad solution
    # but it does seem unintuitive from a user prospective.
    resource_tracker = set()
    for key, value in route_table_properties.items():
        if key.lower() in resource_tracker:
            raise ValueError(
                f"Each property can only be used once. Offending prop: {key}")

        try:
            # this function returns a generic ValueError, so we want to catch
            # it here and propagate it with the correct error message.
            cleaned_property_name: str = validators.validate_props(
                key, value, route_table, lang, EXPECTS_LIST)

        except ValueError as err:
            msg: str = f"{key} is an invalid attribute for RouteTable's."
            raise ValueError(msg) from err

        if key.lower() == "tags":
            formatted_tags = tags.add_tags(
                name, value, callbacks["get_symbol"])
            utils.nested_update(route_table, "Tags", formatted_tags)

        # handle any refs
        validators.resolve_refs(
            cleaned_property_name, route_table, callbacks["get_symbol"])

        resource_tracker.add(key.lower())

    cleaned_route_table: dict[str, Any] = utils.clean(
        route_table, resource_tracker.union(ROUTE_TABLE_DEFAULTS))
    new_route_table = troposphere.ec2.RouteTable(name, **cleaned_route_table)

    # add route table to template
    callbacks["add_resource"](new_route_table)
    # add route table to symbol table
    callbacks["add_symbol"]("routetable", new_route_table)

    # attempt to connect routetable to IGW (if a ref resource exists)
    try:
        callbacks["get_symbol"]("internetgateway")
        _route_to_igw(name, callbacks)

    except KeyError:
        pass


def explain():
    """List the current supported RouteTable properties."""
    # we'll import pprint here as its not that heavily used
    import pprint  # pylint: disable=import-outside-toplevel

    # we can use the typed dict to get this data
    pprint.pprint(get_type_hints(RouteTable))
