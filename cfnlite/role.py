"""Generate a role from CFNLite."""

from typing import Any, Callable, TypedDict, TypeVar, get_type_hints

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


class Policy(TypedDict, total=False):
    """Policy properties."""

    PolicyDocument: PolicyDocument
    PolicyName: str


class Role(TypedDict, total=False):
    """Role properties."""

    AssumeRolePolicyDocument: PolicyDocument
    Description: str
    ManagedPolicyArns: list[str]
    MaxSessionDuration: int
    Path: str
    PermissionsBoundary: str
    Policies: list[Policy]
    RoleName: str


# ensure search/update keys match the hashed key in dicts
KeyType = TypeVar('KeyType')


# Properties that are a list
EXPECTS_LIST: set[str] = {
    "Action",
    "Groups",
    "ManagedPolicyArns",
    "Policies",
    "Resources",
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
    "Arns", "Action", "Assume", "Boundary", "Description", "Document",
    "Duration", "Effect", "Groups", "Managed", "Max", "Name", "Path",
    "Permissions", "Policies", "Policy", "Principal", "Resources", "Role",
    "Roles", "Session", "Sid", "Statement", "Users", "Version",
]


# default fields we always want to generate, even if they're empty
ROLE_DEFAULTS = {"assumerolepolicydocument", "rolename"}


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
    return {
        "PolicyName": "Example cfnlite policy",
        "PolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [],
        },
    }


def _role_defaults():
    """AWS Role with sensible defaults.

    :returns: a dict containing a policy with defaults. Note a user may
        overwrite any of these defaults but the required ones live here to
        give users the option of skipping them in the cfnlite file.
    :rtype: Policy
    """
    defaults = {
        "AssumeRolePolicyDocument": {},
        "Description": "A test role",
        "MaxSessionDuration": 1,
        "Path": "/",
        "PermissionsBoundary": "",
        "Policies": [],
        "RoleName": "TestRole",
    }

    defaults.update(utils.resource_attributes())
    return defaults


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
        raise ValueError(f"'{key}' is an invalid attribute for Roles")

    validated_param = "".join(cleaned_param)

    if validated_param in EXPECTS_LIST and isinstance(value, str):
        value = [value]

    utils.nested_update(props, validated_param, value)

    return validated_param


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


def _handle_policy_document(props: dict[str, Any]) -> Policy:
    """Create a policy document for incoming properties.

    :param dict props: incoming user defined policy properties
    :returns: a correctly formatted policy json object
    :rtype: Policy
    """
    policy: Policy = _policy()

    if not isinstance(props, list):
        props = [props]

    utils.nested_update(policy, "Statement", _handle_statement(props))

    return policy


def build(
    name: str,
    callbacks: CallBacks,
    role_properties: dict[str, Any],
) -> None:
    """Build an role resource from cnflite file.

    :param str name: the cfn name of the resource
    :param CallBacks callbacks: object containing callbacks
    :param dict role_properties: Role properties read in from a cnflite
        file.
    :raises ValueError: if there is an invalid property.
    """
    # holds the final set of correctly formatted Policy properties
    role: Role = _role_defaults()

    # Allow users to overwrite any default value but protect against them
    # naming the same value twice in the cnflite file. This is easily done
    # by naming the same property twice but using different casee i.e.
    # upper/lower for each version of the property.
    # Without this its last entry wins, which isn't necessarily a bad solution
    # but it does seem unintuitive from a user prospective.
    resource_tracker: set[str] = set()
    for key, value in role_properties.items():
        if key.lower() in resource_tracker:
            raise ValueError(
                f"Each property can only be used once. Offending prop: {key}")

        cleaned_property_name: str = _validate_props(key, value, role)

        if cleaned_property_name.lower() == "assumerolepolicydocument":
            assume_policy: Policy = _handle_policy_document(value)
            # AssumeRolePolicyDocument does not need a policy name
            del assume_policy["PolicyName"]
            utils.nested_update(role, "AssumeRolePolicyDocument", assume_policy)

        if cleaned_property_name.lower() == "policies":
            full_policy: Policy = _handle_policy_document(value)
            utils.nested_update(
                role, "Policies",
                # when defining inline policies, troposphere expects a
                # policy object
                [troposphere.iam.Policy(**full_policy)])

        resource_tracker.add(cleaned_property_name.lower())

    # remove any fields that the user did not define but always keep defaults
    cleaned_role: dict[str, str] = utils.clean(
        role, resource_tracker.union(ROLE_DEFAULTS))
    new_role = troposphere.iam.Role(name, **cleaned_role)

    # add ec2 to template
    callbacks["add_resource"](new_role)
    # add ec2 to symbol table
    callbacks["add_symbol"]("role", new_role)


def explain():
    """List the current supported Role properties."""
    # we'll import pprint here as its not that heavily used
    import pprint  # pylint: disable=import-outside-toplevel

    # we can use the typed dict to get this data
    pprint.pprint(get_type_hints(Role))
