"""Generate a NetworkACL from CFNLite."""

from typing import Any, Callable, TypedDict, get_type_hints

from troposphere import Ref, constants
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
#     AWSCloudFormation/latest/UserGuide/aws-resource-ec2-networkacl.html
# )
class NetworkAcl(TypedDict):
    """Protocol for NetworkAcl."""

    Tags: list[TagType]
    VpcId: str


class Icmp(TypedDict):
    """Type interface for an ICMP property in an NACL Entry."""

    Code: int
    Type: int


class PortRange(TypedDict):
    """Type interface for an PortRange property in an NACL Entry."""

    From: int
    To: int


class NaclEntry(TypedDict):
    """Type interface for NACL Entry props."""

    CidrBlock: str
    Egress: bool
    Icmp: Icmp
    Ipv6CidrBlock: str
    NetworkAclId: str
    PortRange: PortRange
    Protocol: int
    RuleAction: str
    RuleNumber: int


# NACL values that expect a list
EXPECTS_LIST: set[str] = set("Tags")


LANG: list[str] = [
    "Action", "Acl", "Block", "Cidr", "Egress", "Icmp", "Id", "Ingress",
    "Ipv6", "Network", "Number", "Port", "Protocol", "Range", "Rule", "Tags",
    "Vpc"
]

# map standard network protocols to their ports
# NOTE: ICMP is weird so just ignore it
PORT_MAP: dict[str, int] = {
    "icmp": 0,
    "mysql": 3306,
    "http": constants.HTTP_PORT,
    "https": constants.HTTPS_PORT,
    "memcached": constants.MEMCACHED_PORT,
    "mongo": constants.MONGODB_PORT,
    "ntp": constants.NTP_PORT,
    "psql": constants.POSTGRESQL_PORT,
    "redis": constants.REDIS_PORT,
    "smtp": constants.SMTP_PORT_25,
    "ssh": constants.SSH_PORT,
}


# required props
NAT_ACL_DEFAULTS: set[str] = {
    "networkaclid",
    "portrange",
    "protocol",
    "ruleaction",
    "rulenumber",
    "vpcid",
}


def _default_nat_acl() -> NetworkAcl:
    """Generate a NACL resource.

    :returns: A NACL resource with defaults
    :rtype: NetworkAcl
    """
    defaults: dict[str, str | list[TagType]] = {
        "Tags": [],
        "VpcId": "id-example-vpc",
    }

    defaults.update(utils.resource_attributes())
    return defaults


def _port_range(port: int = 80) -> troposphere.ec2.PortRange:
    """Generate a PortRange for a NACL entry.

    :param int port: the port number needed for the entry protocol
    :returns: a CNF port range
    :rtype: troposphere.ec2.PortRange
    """
    range_: PortRange = {
        "From": port,
        "To": port,
    }

    return troposphere.ec2.PortRange(**range_)


def _icmp(type_: int = 0) -> troposphere.ec2.ICMP:
    """Generate a ICMP route for a NACL entry.

    :param int type: the type number needed for the ICMP request/response
    :returns: a CNF ICMP
    :rtype: troposphere.ec2.ICMP
    """
    icmp: Icmp = {
        "Code": 0,
        "Type": type_,
    }

    return troposphere.ec2.ICMP(**icmp)


def _nat_acl_entry_rule_defaults() -> NaclEntry:
    """NACL Entry defaults.

    :returns: A NACL entry with some defaults
    :rtype: NaclEntry
    """
    defaults: NaclEntry = {
        "CidrBlock": "0.0.0.0/0",
        "Egress": False,
        "Icmp": {
            "Code": 0,
            "Type": 0,
        },
        "NetworkAclId": "id-example-Nacl",
        "PortRange": {
            "From": constants.HTTP_PORT,
            "To": constants.HTTP_PORT,
        },
        "Protocol": constants.TCP_PROTOCOL,
        "RuleAction": "allow",
        "RuleNumber": constants.HTTP_PORT,
    }

    return defaults


def tcp_rule(protocol: str) -> NaclEntry:
    """Generate a TCP NACL entry.

    :returns: a valid NACL entry for a given protocol
    :rtype: NaclEntry
    """
    # if protocol is unknown, default to http
    port: int = (
        PORT_MAP[protocol]
        if protocol in PORT_MAP
        else constants.HTTP_PORT
    )
    nat_rule: NaclEntry = _nat_acl_entry_rule_defaults()

    utils.nested_update(nat_rule, "Protocol", constants.TCP_PROTOCOL)
    utils.nested_update(nat_rule, "PortRange", _port_range(port))
    utils.nested_update(nat_rule, "RuleNumber", port)

    # You only need one of ICMP/PortRange
    del nat_rule["Icmp"]

    return nat_rule


def icmp_rule(type_: int) -> NaclEntry:
    """Generate a ICMP NACL entry.

    :returns: a valid NACL ICMP entry
    :rtype: NaclEntry
    """
    nat_rule: NaclEntry = _nat_acl_entry_rule_defaults()

    utils.nested_update(nat_rule, "Protocol", constants.ICMP_PROTOCOL)
    utils.nested_update(nat_rule, "Icmp", _icmp(type_))
    utils.nested_update(nat_rule, "RuleNumber", 100)

    # You only need one of ICMP/PortRange
    del nat_rule["PortRange"]

    return nat_rule


def nat_rules(
    name: str,
    protocols: list[str],
    callbacks: CallBacks,
    egress: bool = False,
) -> None:
    """Generate NACL entries for each protocol.

    :param str name: name of the parent resource
    :param list protocols: list of NACL entry protocols
    :param CallBacks callbacks: callback functions
    :param bool egress: egress entries, if false entries are ingress
    """
    # get a reference to the NACL resource
    nat_acl: Ref = Ref(callbacks["get_symbol"]("networkacl"))

    for protocol in protocols:
        # we have to deal with ICMP separately as its not actually
        # an application layer protocol (its a layer 3 proto)
        if protocol.lower() == "icmp":
            rule: NaclEntry = icmp_rule(8 if not egress else 0)

        else:
            rule: NaclEntry = tcp_rule(protocol)

        utils.nested_update(rule, "NetworkAclId", nat_acl)
        utils.nested_update(rule, "Egress", egress)

        rule = troposphere.ec2.NetworkAclEntry(
            f"{name}Rule{protocol.upper()}{'In' if not egress else 'Out'}",
            **rule)

        callbacks["add_resource"](rule)


def build(
    name: str,
    callbacks: CallBacks,
    nat_acl_properties: dict[str, str],
) -> None:
    """Build an NetworkAcl resource from a cfnlite definition.

    :param str name: the cfn name for the resource
    :param CallBacks callbacks: object containing callbacks
    :param dict nat_acl_properties: NACL props read in from a cfnlit file.

    :raises ValueError: if there is an invalid property.
    """
    # holds the final set of correctly formatted NACL properties to pass into
    # the cfn generator
    nat_acl: NetworkAcl = _default_nat_acl()

    # Unlike SGs, we neet to make NACL entries after we make and register
    # the NACL resource. To simplify creating NACL entries, cfnlite introduces
    # two _cfnlite specific_ keywords for NACL resources - ingress, egress.
    # These keywords allow users to pass in a list of NACL rules similar to how
    # we handle SGs, to simplify the devUx. As a result we have to manually
    # handle these keywords and create the appropriate entries. This list holds
    # which ever of ingress/egress is defined (or both) and creates the
    # passed rules after we build the NACL.
    rule_directions: list[str] = []

    # Allow users to overwrite any default value but protect against them
    # naming the same value twice in the cnflite file. This is easily done
    # by naming the same property twice but using different casee i.e.
    # upper/lower for each version of the property.
    # Without this its last entry wins, which isn't necessarily a bad solution
    # but it does seem unintuitive from a user prospective.
    resource_tracker: set[str] = set()
    for key, value in nat_acl_properties.items():
        if key.lower() in resource_tracker:
            raise ValueError(
                f"Each property can only be used once. Offending prop: {key}")

        try:
            # this function returns a generic ValueError, so we want to catch
            # it here and propagate it with the correct error message.
            cleaned_property_name: str = validators.validate_props(
                key, value, nat_acl, LANG, EXPECTS_LIST)

        except ValueError as err:
            msg: str = f"{key} is an invalid attribute for NetworkAcl's."
            raise ValueError(msg) from err

        if cleaned_property_name.lower() in ("egress", "ingress"):
            # save the name and move one, we handle the rules later
            rule_directions.append(cleaned_property_name.lower())
            continue

        if key.lower() == "tags":
            formatted_tags = tags.add_tags(name, value, callbacks["get_symbol"])
            utils.nested_update(nat_acl, "Tags", formatted_tags)

        validators.resolve_refs(
            cleaned_property_name, nat_acl, callbacks["get_symbol"])

        resource_tracker.add(key.lower())

    cleaned_nat_acl: dict[str, Any] = utils.clean(
        nat_acl, resource_tracker.union(NAT_ACL_DEFAULTS))
    new_nat_acl = troposphere.ec2.NetworkAcl(name, **cleaned_nat_acl)

    # add ec2 to template
    callbacks["add_resource"](new_nat_acl)
    # add ec2 to symbol table
    callbacks["add_symbol"]("networkacl", new_nat_acl)

    # add rules after
    for direction in rule_directions:
        protos = nat_acl_properties[direction]
        # for a single protocol users can put in a string instead of
        # a one protocol list. This covers that case.
        if isinstance(protos, str):
            protos = [protos]

        nat_rules(
            name,
            protos,
            callbacks,
            egress=direction.lower() == "egress"
        )


def explain():
    """List the current supported NACL properties."""
    # we'll import pprint here as its not that heavily used
    import pprint  # pylint: disable=import-outside-toplevel

    # we can use the typed dict to get this data
    pprint.pprint(get_type_hints(NetworkAcl))
