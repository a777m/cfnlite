"""Generate EC2 resources from CFNLite."""

from typing import Any, Callable, TypedDict, get_type_hints

from troposphere import Ref
import troposphere.ec2

from cfnlite.lib import utils


# Callbacks type, just to sure things up for people with cool IDEs
class CallBacks(TypedDict):
    """Types for each of the callback function signatures."""

    add_symbol: Callable[[str, Any], None]
    get_symbol: Callable[[str], Any]
    add_resource: Callable[[Any], None]


# details: (
#    https://docs.aws.amazon.com/ \
#    AWSCloudFormation/latest/UserGuide/aws-resource-ec2-instance.html
# )
class EC2(TypedDict, total=False):
    """The EC2 attributes we currently support."""

    AdditionalInfo: str
    Affinity: str
    AvailabilityZone: str
    BlockDeviceMappings: list[Any]
    DisableApiTermination: bool
    EbsOptimized: bool
    HostId: str
    HostResourceGroupArn: str
    IamInstanceProfile: str
    ImageId: str
    InstanceInitiatedShutdownBehavior: str
    InstanceType: str
    KernelId: str
    KeyName: str
    Monitoring: bool
    NetworkInterfaces: list[Any]
    PlacementGroupName: str
    PrivateIpAddress: str
    SecurityGroupIds: list[str]
    SecurityGroups: list[str]
    SubnetId: str
    Tenancy: str
    Volumes: list[Any]


# Properties that are a list
EXPECTS_LIST: set[str] = {
    "BlockDeviceMappings",
    "NetworkInterfaces",
    "SecurityGroupIds",
    "SecurityGroups",
    "Volumes",
}


# "Lang" is a misnomer here but essentially in order to allow users to not
# need to strictly adhere to the PascalCase required by CNF we need to be able
# to recreate the correct form for each property. This list holds all the words
# that are combined together to make up any allowed EC2 property. This is then
# fed into our "resolver" functionality which spits out the the correct cased
# property name. As a result, properties must still be spelt correctly, however,
# any casing combination is allowed.
LANG: list[str] = [
    "Additional", "Address", "Affinity", "Api", "Arn", "Availability",
    "Behavior", "Block", "Device", "Disable", "Ebs", "Group", "Groups", "Host",
    "Iam", "Id", "Ids", "Image", "Info", "Initiated", "Instance", "Interfaces",
    "Ip", "Kernel", "Key", "Mappings", "Monitoring", "Name", "Network",
    "Optimized", "Placement", "Private", "Profile", "Resource", "Security",
    "Shutdown", "Subnet", "Tenancy", "Termination", "Type", "Volumes", "Zone"
]


def _default_ec2_params() -> EC2:
    """EC2 parameters we sensible defaults.

    :returns: a dict containing EC2 defaults we want to use. Note a user may
        overwrite any of these defaults but the required ones live here to
        give users the option of skipping them in the cfnlite file.
    :rtype: EC2
    """
    return {
        "ImageId": "ami-0b45ae66668865cd6",
        "InstanceType": "t2.micro",
        "SecurityGroups": ["default"]
    }


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
    props: EC2,
    callback: Callable[[str], Any]
) -> None:
    """Resolve any references the property needs.

    :param str prop_name: the property name
    :param EC2 props: object holding final set of correctly formatted props
        passed down to the resource generator
    :param Callable callback: callback to help resolve references
    """
    if prop_name in EXPECTS_LIST:
        props[prop_name] = _check_list_for_refs(props[prop_name], callback)

    elif (
        isinstance(props[prop_name], str)
        and props[prop_name].strip().startswith("ref")
    ):
        props[prop_name] = _handle_refs(props[prop_name], callback)


def _validate_props(
    key: str,
    value: str | list[str],
    props: EC2,
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
        props[validated_param] = [value]

    else:
        props[validated_param] = value

    return validated_param


def build(
    name: str,
    callbacks: CallBacks,
    ec2_properties: dict[str, Any]
) -> None:
    """Build an EC2 resource from cnflite file.

    :param str name: the cfn name of the resource
    :param CallBacks callbacks: object containing callbacks
    :param dict ec2_properties: EC2 properties read in from a cnflite
        file.
    :raises ValueError: if there is an invalid property.
    """
    # holds the final set of correctly formatted EC2 properties to pass into
    # the cfn generator
    ec2 = _default_ec2_params()

    # Allow users to overwrite any default value but protect against them
    # naming the same value twice in the cnflite file. This is easily done
    # by naming the same property twice but using different casee i.e.
    # upper/lower for each version of the property.
    # Without this its last entry wins, which isn't necessarily a bad solution
    # but it does seem unintuitive from a user prospective.
    resource_tracker = set()
    for key, value in ec2_properties.items():
        if key.lower() in resource_tracker:
            raise ValueError(
                f"Each property can only be used once. Offending prop: {key}")

        cleaned_property_name = _validate_props(key, value, ec2)
        # handle any refs
        resolve_refs(cleaned_property_name, ec2, callbacks["get_symbol"])

        resource_tracker.add(key.lower())

    new_ec2 = troposphere.ec2.Instance(name, **ec2)

    # add ec2 to template
    callbacks["add_resource"](new_ec2)
    # add ec2 to symbol table
    callbacks["add_symbol"]("ec2", new_ec2)


def explain():
    """List the current supported EC2 properties."""
    # we'll import pprint here as its not that heavily used
    import pprint  # pylint: disable=import-outside-toplevel

    # we can use the typed dict to get this data
    pprint.pprint(get_type_hints(EC2))
