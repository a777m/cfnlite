"""Generate a policy document from CFNLite file."""

from typing import Any, Callable, TypedDict, TypeVar, get_type_hints

import troposphere.iam

from cfnlite.lib import utils, validators


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

    # lang is localised for policy statements
    lang: list[str] = utils.create_lang(_statement().keys())

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
            cleaned_prop: str = validators.validate_props(
                key, value, default_statement, lang, EXPECTS_LIST)

            resource_tracker.add(cleaned_prop.lower())

        cleaned_statement: dict[str, Any] = utils.clean(
            default_statement, resource_tracker.union(default_statement_props))
        res.append(cleaned_statement)

    return res


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

    # The nested-ness of policy documents makes this AITA but its still
    # better to use the auto generated approach and keep in line with the
    # rest of the code than to be out of lock step
    lang: list[str] = utils.create_lang(
        list(policy.keys())
        + list(_statement().keys())
        + ["Statement"]
        + ["Version"]
    )

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

        try:
            # this function returns a generic ValueError, so we want to catch
            # it here and propagate it with the correct error message.
            cleaned_property_name: str = validators.validate_props(
                key, value, policy, lang, EXPECTS_LIST)

        except ValueError as err:
            msg: str = f"'{key}' is an invalid attribute for Policies"
            raise ValueError(msg) from err

        if cleaned_property_name.lower() == "statement":
            utils.nested_update(policy, "Statement", _handle_statement(value))

        # handle any refs
        validators.resolve_refs(
            cleaned_property_name, policy, callbacks["get_symbol"])

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
