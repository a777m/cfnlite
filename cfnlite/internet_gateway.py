"""Generate an IGW from CFNlite."""

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
#     AWSCloudFormation/latest/UserGuide/aws-resource-ec2-internetgateway.html
# )
class IGW(TypedDict):
    """Types for internet gateway."""

    Tags: list[TagType]


def _default_igw_params() -> IGW:
    """Default internet gateway properties.

    :return: a dict containing IGW default props
    :rtype: IGW
    """
    defaults: dict[str, list[TagType]] = {
        "Tags": [],
    }

    defaults.update(utils.resource_attributes())
    return defaults


def _vpc_gateway_attachment(name: str, callbacks: CallBacks) -> None:
    """Generate VPC gateway attachment.

    :param str name: name of parent resource
    :param CallBacks callbacks: call back object
    """
    attachment: dict[str, Ref] = {
        "InternetGatewayId": Ref(callbacks["get_symbol"]("internetgateway")),
        "VpcId": Ref(callbacks["get_symbol"]("vpc")),
    }

    gateway_attachement = troposphere.ec2.VPCGatewayAttachment(
        f"{name}Attachement", **attachment)

    callbacks["add_resource"](gateway_attachement)


def build(
    name: str,
    callbacks: CallBacks,
    igw_properties: dict[str, str],
) -> None:
    """Build an internet gateway resource from a cfnlite definition.

    :param str name: the cfn name for the resource
    :param CallBacks callbacks: object containing callbacks
    :param dict igw_properties: IGW props read in from a cfnlit file.

    :raises ValueError: if there is an invalid property.
    """
    # holds the final set of correctly formatted IGW properties to pass into
    # the cfn generator
    igw: IGW = _default_igw_params()

    lang: list[str] = utils.create_lang(igw.keys())

    # Allow users to overwrite any default value but protect against them
    # naming the same value twice in the cnflite file. This is easily done
    # by naming the same property twice but using different casee i.e.
    # upper/lower for each version of the property.
    # Without this its last entry wins, which isn't necessarily a bad solution
    # but it does seem unintuitive from a user prospective.
    resource_tracker: set[str] = set()
    for key, value in igw_properties.items():
        if key.lower() in resource_tracker:
            raise ValueError(
                f"Each property can only be used once. Offending prop: {key}")

        try:
            # this function returns a generic ValueError, so we want to catch
            # it here and propagate it with the correct error message.
            validators.validate_props(key, value, igw, lang, set("Tags"))

        except ValueError as err:
            msg: str = f"{key} is an invalid attribute for IGW's."
            raise ValueError(msg) from err

        if key.lower() == "tags":
            formatted_tags = tags.add_tags(
                name, value, callbacks["get_symbol"])
            utils.nested_update(igw, "Tags", formatted_tags)

        resource_tracker.add(key.lower())

    cleaned_igw: dict[str, Any] = utils.clean(
        igw, resource_tracker.union(set("Tags")))
    new_igw = troposphere.ec2.InternetGateway(name, **cleaned_igw)

    # add ec2 to template
    callbacks["add_resource"](new_igw)
    # add ec2 to symbol table
    callbacks["add_symbol"]("internetgateway", new_igw)

    # check if there is a vpc defined as part of the cnflite file, if there is
    # we generate a gateway attachement resource.
    # * this may be a parameter option rather than directly created in the
    # same config
    try:
        callbacks["get_symbol"]("vpc")
        _vpc_gateway_attachment(name, callbacks)

    except KeyError:
        pass


def explain():
    """List the current supported IGW properties."""
    # we'll import pprint here as its not that heavily used
    import pprint  # pylint: disable=import-outside-toplevel

    # we can use the typed dict to get this data
    pprint.pprint(get_type_hints(IGW))
