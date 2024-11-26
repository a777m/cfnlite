"""Generate Security Groups from CNFLite."""

from typing import Any, Callable, TypedDict

from troposphere import GetAtt
import troposphere.ec2

from cfnlite.lib import utils


# Callbacks type, just to sure things up for people with cool IDEs
class CallBacks(TypedDict):
    """Types for each of the callback function signatures."""

    add_symbol: Callable[[str, Any], None]
    get_symbol: Callable[[str], Any]
    add_resource: Callable[[Any], None]


# details: (
#     https://docs.aws.amazon.com/ \
#     AWSCloudFormation/latest/UserGuide/aws-resource-ec2-securitygroup.html
# )
class SecurityGroup(TypedDict, total=False):
    """SG types."""

    GroupDescription: str
    GroupName: str
    SecurityGroupEgress: list[troposphere.ec2.SecurityGroupEgress]
    SecurityGroupIngress: list[troposphere.ec2.SecurityGroupIngress]
    VpcId: str


class SecurityGroupRule(TypedDict, total=False):
    """Security Group Rule types."""

    CidrIp: str
    Description: str
    FromPort: int
    GroupId: str
    IpProtocol: str
    ToPort: int


# Type for security group rules list
SGRulesList = list[
    troposphere.ec2.SecurityGroupEgress
    | troposphere.ec2.SecurityGroupEgress
]


# Properties that are a list
EXPECTS_LIST: set[str] = {"SecurityGroupEgress", "SecurityGroupIngress"}


# "Lang" is a misnomer here but essentially in order to allow users to not
# need to strictly adhere to the PascalCase required by CNF we need to be able
# to recreate the correct form for each property. This list holds all the words
# that are combined together to make up any allowed EC2 property. This is then
# fed into our "resolver" functionality which spits out the the correct cased
# property name. As a result, properties must still be spelt correctly, however,
# any casing combination is allowed.
LANG: list[str] = [
    "Description", "Egress", "Group", "Id", "Ingress", "Name",
    "Security", "Vpc",
]


# map standard network protocols to their ports
# NOTE: ICMP is weird so just ignore it
PORT_MAP: dict[str, int] = {
    "http": 80,
    "https": 443,
    "icmp": 0,
    "ssh": 22,
}


# defaults are lower case as thats makes comparisions consistent
# i.e. str.lower() can be used to compare strings
SG_DEFAULTS: set[str] = {
    "groupdescription",
    "securitygroupegress",
    "securitygroupingress",
}


def _security_group_rule_defaults(
    protocol: str = "tcp",
    from_port: int = 80,
    to_port: int = 80,
) -> SecurityGroupRule:
    """Security Group rule with sensible defaults.

    :param str protocol: The IP protocol for the rule e.g. tcp
    :param int from_port: Port associated with the protocol e.g. 80 for http
    :param int to_port: Port associated with the protocol e.g. 80 for http

    :returns: a security group rules object with some defaults
    :rtype: SecurityGroupRule
    """
    return {
        "CidrIp": "0.0.0.0/0",
        "GroupId": "",
        "Description": "An in/out-bound SecurityGroup rule",
        "IpProtocol": protocol,
        "FromPort": from_port,
        "ToPort": to_port,
    }


def _security_group_defaults() -> SecurityGroup:
    """Security group defaults.

    :returns: A security groups object with some defaults
    :rtype: SecurityGroup
    """
    defaults: SecurityGroup = {
        "GroupDescription": "",
        "GroupName": "default-group-name",
        "SecurityGroupEgress": [],
        "SecurityGroupIngress": [],
        "VpcId": "",
    }

    defaults.update(utils.resource_attributes())
    return defaults


def rules(
    sg_name: str,
    prop_name: str,
    protocols: list[str]
) -> SGRulesList:
    """Handle inbound/outbound security group rules.

    :param str prop_name: the name of the property
    :param str sg_name: security group name
    :param list[str] protocols: list of protocols to allow

    :return: a list of security group ingress/egress rules
    :rtype: SGRulesList
    """
    result: SGRulesList = []
    # dynamically get the rule class depending on the property name
    # this will be troposphere.ece.{SecurityGroupEgress,SecurityGroupIngress}
    security_group_object: object = getattr(troposphere.ec2, prop_name)

    for protocol in protocols:
        # handle unknown values, dont abort generate generic http
        port: int = PORT_MAP[protocol] if protocol in PORT_MAP else 80
        # CFN SGs dont actually accept the application layer (layer 7) protocol
        # e.g. http but rather require the transport layer (layer 4) protocol
        # e.g. tcp/udp.
        # All application layer protocols we support are tcp but icmp is not an
        # application layer protocol so must be handled separately.
        proto: str = "icmp" if protocol.lower() == "icmp" else "tcp"

        sg_rule: SecurityGroupRule = _security_group_rule_defaults(
            proto, from_port=port, to_port=port)

        sg_rule["GroupId"] = GetAtt(sg_name, "GroupId")

        if prop_name == "SecurityGroupEgress":
            sg_rule["Description"] = f"Outbound {protocol.upper()} traffic"

        elif prop_name == "SecurityGroupIngress":
            sg_rule["Description"] = f"Inbound {protocol.upper()} traffic"
            # ToPort is the same on both ingress and egress for all protocols
            # however, ICMP requires a special FromPort value for ingress
            sg_rule["FromPort"] = 8 if protocol.lower() == "icmp" else port

        result.append(security_group_object(
            f"{prop_name}{protocol.upper()}{port}", **sg_rule))

    return result


def _validate_params(
    key: str,
    value: str | list[str],
    props: SecurityGroup,
) -> str:
    """Validate incoming resource properties.

    :param str key: the property name
    :param str | list[str] value: the property value(s)
    :param SecurityGroup props: object holding final set of correctly
        formatted props passed down to the resource generator

    :returns: correctly formatted property name
    :rtype: str
    :raises ValueError: if key is an invalid SG property
    """
    cleaned_property = utils.property_validator(key, LANG)
    if not cleaned_property:
        raise ValueError(f"{key} is not a valid attribute for SecurityGroups")

    validated_param: str = "".join(cleaned_property)

    if validated_param in EXPECTS_LIST and isinstance(value, str):
        value = [value]

    utils.nested_update(props, validated_param, value)

    return validated_param


def build(
    name: str,
    callbacks: CallBacks,
    sg_properties: dict[str, Any]
) -> None:
    """Build an Security Groups resource from cnflite file.

    :param str name: the cfn name of the resource
    :param CallBacks callbacks: object containing callbacks
    :param dict sg_properties: SG properties read in from a cnflite
        file.
    :raises ValueError: if there is an invalid property.
    """
    # holds the final set of correctly formatted SGs properties to pass into
    # the cfn generator
    sgs = _security_group_defaults()

    # Allow users to overwrite any default value but protect against them
    # naming the same value twice in the cnflite file. This is easily done
    # by naming the same property twice but using different casee i.e.
    # upper/lower for each version of the property.
    # Without this its last entry wins, which isn't necessarily a bad solution
    # but it does seem unintuitive from a user prospective.
    resource_tracker = set()
    for key, value in sg_properties.items():
        if key.lower() in resource_tracker:
            raise ValueError(
                f"Each property can only be used once. Offending prop: {key}")

        cleaned_property_name = _validate_params(key, value, sgs)

        if cleaned_property_name in EXPECTS_LIST:
            in_out_rules = rules(
                sg_name=name,
                prop_name=cleaned_property_name,
                # the reason we use hashed value rather than the incoming value
                # is because _validate_params essentially 'cleans' up the value
                # by making sure its in a list if it comes in as a string, this
                # will usually be the case for a single rule
                protocols=utils.nested_find(sgs, cleaned_property_name))

            # update sgs dict
            utils.nested_update(sgs, cleaned_property_name, in_out_rules)

        resource_tracker.add(cleaned_property_name.lower())

    cleaned_sgs: dict[str, Any] = utils.clean(
        sgs, resource_tracker.union(SG_DEFAULTS))
    new_sg = troposphere.ec2.SecurityGroup(name, **cleaned_sgs)

    # add ec2 to template
    callbacks["add_resource"](new_sg)
    # add ec2 to symbol table
    callbacks["add_symbol"]("securitygroups", new_sg)
