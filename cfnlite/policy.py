"""Generate a policy document from CFNLite file."""

from typing import Any, Callable, TypedDict, TypeVar, get_type_hints

from troposphere import Ref
import troposphere.iam

from cfnlite.lib import utils


# Callbacks type, just to sure things up for people with cool IDEs
class CallBacks(TypedDict):
    """Types for each of the callback function signatures."""

    add_symbol: Callable[[str, Any], None]
    get_symbol: Callable[[str], Any]
    add_resource: Callable[[Any], None]


class Statement(TypedDict, total=False):
    """Statement properties."""

    Action: list[str]
    Effect: str
    Principal: dict[str, str]
    Resources: list[str]
    Sid: str


class PolicyDocument(TypedDict, total=False):
    """Policy document properties."""

    Statement: list[Statement]
    Version: str


# details: (
#     https://docs.aws.amazon.com/ \
#     AWSCloudFormation/latest/UserGuide/aws-resource-iam-policy.html
# )
class Policy(TypedDict, total=False):
    """Policy properties."""

    Groups: list[str]
    PolicyDocument: PolicyDocument
    PolicyName: str
    Roles: list[str]
    Users: list[str]


# ensure search/update keys match the hashed key in dicts
KeyType = TypeVar('KeyType')


# Properties that are a list
EXPECTS_LIST: set[str] = {
    "Action",
    "Groups",
    "Resources",
    "Roles",
    "Statement",
    "Users"
}


# "Lang" is a misnomer here but essentially in order to allow users to not
# need to strictly adhere to the PascalCase required by CNF we need to be able
# to recreate the correct form for each property. This list holds all the words
# that are combined together to make up any allowed EC2 property. This is then
# fed into our "resolver" functionality which spits out the the correct cased
# property name. As a result, properties must still be spelt correctly, however,
# any casing combination is allowed.
LANG: list[str] = [
    "Action", "Document", "Effect", "Groups", "Name", "Policy", "Principal",
    "Resources", "Roles", "Sid", "Statement", "Users", "Version",
]


# defaults are lower case as thats makes comparisions consistent
# i.e. str.lower() can be used to compare strings
POLICY_DEFAULTS: set[str] = {"policyname", "policydocument"}


def _statement() -> Statement:
    """Policy statement with sensible defaults.

    :returns: a dict containing policy statement defaults. Note a user may
        overwrite any of these defaults but the required ones live here to
        give users the option of skipping them in the cfnlite file.
    :rtype: Statement
    """
    return {
        "Action": [],
        "Effect": "Allow",
        "Principal": {},
        "Resources": ["*"],
        "Sid": "ExampleStatement",
    }


def _policy() -> Policy:
    """AWS policy with sensible defaults.

    :returns: a dict containing a policy with defaults. Note a user may
        overwrite any of these defaults but the required ones live here to
        give users the option of skipping them in the cfnlite file.
    :rtype: Policy
    """
    defaults: Policy = {
        "Groups": [],
        "PolicyName": "Example cfnlite policy",
        "PolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [],
        },
        "Roles": [],
        "Users": [],
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


def _handle_statement(statements: list[dict[str, str]]) -> list[Statement]:
    """Correctly format incoming policy statements.

    cfnlite offers users a simplified interface for creating CFN templates,
    a part of this is flattening the property definitions unlike normal CFN
    templates which require a lot of nesting.

    In order to generate the correct CFN template cfnlite needs to handle
    the arbitrary nesting of CFN policy definitions. This function handles
    generating the correct output for each of the incoming, flattened, policy
    document statements.

    Simply put, for each policy document statement, this function generates
    a dict with statement defaults and updates each property in the default
    with the corresponding incoming property.

    :param list[dict] statements: a list containing user defined policy
        statements
    :returns: correctly formatted policy document statements
    :rtype: list[Statement]
    """
    default_statement_props: set[str] = {"action", "effect", "resources"}
    res: list[Statement] = []

    for statement in statements:

        default_statement: Statement = _statement()
        # prevent users defining the same resource twice
        resource_tracker: set[str] = set()

        for key, value in statement.items():
            if key.lower() in resource_tracker:
                raise ValueError(
                    "Statement properties can only be defined once. "
                    f"Offending key: {key}")
            # clean the incoming key and update the default value to
            # incoming one
            cleaned_prop: str = _validate_props(key, value, default_statement)

            resource_tracker.add(cleaned_prop.lower())

        cleaned_statement: dict[str, Any] = utils.clean(
            default_statement, resource_tracker.union(default_statement_props))
        res.append(cleaned_statement)

    return res


def _validate_props(
    key: KeyType,
    value: str | list[str | dict[str, Any]],
    props: dict[KeyType, Any]
) -> KeyType:
    """Validate incoming resource properties.

    :param KeyType key: the property name
    :param str | list[str | dict[str, Any]] value: the property value(s)
    :param dict[KeyType, Any] props: object holding final set of correctly
        formatted props passed down to the resource generator

    :returns: correctly formatted property name
    :rtype: KeyType
    :raises ValueError: if key is an invalid EC2 property
    """
    cleaned_param = utils.property_validator(key, LANG)
    if not cleaned_param:
        raise ValueError(f"'{key}' is an invalid attribute for Policies")

    validated_param = "".join(cleaned_param)

    if validated_param in EXPECTS_LIST and isinstance(value, str):
        value = [value]

    utils.nested_update(props, validated_param, value)

    return validated_param


def resolve_refs(
    prop_name: str,
    props: dict,
    callback: Callable[[str], Any]
) -> None:
    """Resolve any references the property needs.

    :param str prop_name: the property name
    :param dict props: object holding final set of correctly formatted props
        passed down to the resource generator
    :param Callable callback: get symbol callback to resolve references
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


def build(
    name: str,
    callbacks: CallBacks,
    policy_properties: dict[str, Any],
) -> None:
    """Build an policy resource from cnflite file.

    :param str name: the cfn name of the resource
    :param CallBacks callbacks: object containing callbacks
    :param dict policy_properties: Policy properties read in from a cnflite
        file.
    :raises ValueError: if there is an invalid property.
    """
    # holds the final set of correctly formatted Policy properties
    policy: Policy = _policy()

    # Allow users to overwrite any default value but protect against them
    # naming the same value twice in the cnflite file. This is easily done
    # by naming the same property twice but using different casee i.e.
    # upper/lower for each version of the property.
    # Without this its last entry wins, which isn't necessarily a bad solution
    # but it does seem unintuitive from a user prospective.
    resource_tracker: set[str] = set()
    for key, value in policy_properties.items():
        if key.lower() in resource_tracker:
            raise ValueError(
                f"Each property can only be used once. Offending prop: {key}")

        cleaned_property_name: str = _validate_props(key, value, policy)

        if cleaned_property_name.lower() == "statement":
            utils.nested_update(policy, "Statement", _handle_statement(value))

        # handle any refs
        resolve_refs(cleaned_property_name, policy, callbacks["get_symbol"])

        resource_tracker.add(cleaned_property_name.lower())

    # remove any fields that the user did not define but always keep defaults
    cleaned_policy: dict[str, str] = utils.clean(
        policy, resource_tracker.union(POLICY_DEFAULTS))
    new_policy = troposphere.iam.PolicyType(name, **cleaned_policy)

    # add ec2 to template
    callbacks["add_resource"](new_policy)
    # add ec2 to symbol table
    callbacks["add_symbol"]("policy", new_policy)


def explain():
    """List the current supported Policies properties."""
    # we'll import pprint here as its not that heavily used
    import pprint  # pylint: disable=import-outside-toplevel

    # we can use the typed dict to get this data
    pprint.pprint(get_type_hints(Policy))
