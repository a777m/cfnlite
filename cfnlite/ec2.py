"""Generate EC2 resources from CFNLite."""

from typing import Any, Callable, TypedDict, get_type_hints

import troposphere.ec2

from cfnlite.lib import utils, validators


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


EC2_DEFAULTS: set[str] = {"imageid", "instancetype", "securitygroups"}


def _default_ec2_params() -> EC2:
    """EC2 parameters we sensible defaults.

    :returns: a dict containing EC2 defaults we want to use. Note a user may
        overwrite any of these defaults but the required ones live here to
        give users the option of skipping them in the cfnlite file.
    :rtype: EC2
    """
    defaults: EC2 = {
        "AdditionalInfo": "",
        "Affinity": "",
        "AvailabilityZone": "",
        "BlockDeviceMappings": [],
        "DisableApiTermination": False,
        "EbsOptimized": False,
        "HostId": "",
        "HostResourceGroupArn": "",
        "IamInstanceProfile": "",
        "ImageId": "ami-0b45ae66668865cd6",
        "InstanceInitiatedShutdownBehavior": "",
        "InstanceType": "t2.micro",
        "KernelId": "",
        "KeyName": "",
        "Monitoring": False,
        "NetworkInterfaces": [],
        "PlacementGroupName": "",
        "PrivateIpAddress": "",
        "SecurityGroupIds": [],
        "SecurityGroups": ["default"],
        "SubnetId": "",
        "Tenancy": "",
        "Volumes": [],
    }

    defaults.update(utils.resource_attributes())
    return defaults


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

        try:
            # this function returns a generic ValueError, so we want to catch
            # it here and propagate it with the correct error message.
            cleaned_property_name = validators.validate_props(
                key, value, ec2, LANG, EXPECTS_LIST)

        except ValueError as err:
            msg: str = f"{key} is an invalid attribute for EC2's."
            raise ValueError(msg) from err
        # handle any refs
        validators.resolve_refs(
            cleaned_property_name, ec2, EXPECTS_LIST, callbacks["get_symbol"])

        resource_tracker.add(key.lower())

    # remove any fields that the user did not define but always keep defaults
    cleaned_ec2 = utils.clean(
        ec2, resource_tracker.union(EC2_DEFAULTS))
    new_ec2 = troposphere.ec2.Instance(name, **cleaned_ec2)

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
