"""cfnlite utilities."""
from typing import Any, TypeVar

# ensure search keys match the hashed key in dicts
KeyType = TypeVar('KeyType')

# These are default aws resource attributes, they site outside resource props
# but can be used as props on any given resource. We need to check these as
# well as the normal range of words associated with resource props.
RESOURCE_ATTR: list[str] = [
    "Creation", "Deletion", "Depends", "Metadata", "On",
    "Policy", "Replace", "Update",
]


def resource_attributes() -> dict[str, Any]:
    """A dict containing aws resource attributes with defaults."""
    return {
        "CreationPolicy": {},
        "DeletionPolicy": "Delete",
        "DependsOn": [],
        "MetaData": {},
        "UpdatePolicy": {},
        "UpdateReplacePolicy": "Delete",
    }


def property_validator(
    property: str,  # pylint: disable=redefined-builtin
    choices: list[str],
) -> list[str]:
    """Validate a given resource property.

    "Validate" might not necessarily completely correct. At its core, we
    allow users to name resource properties in a case insensitive way e.g.
    ("securitygroups", "Securitygroups", "securityGroups") are all valid
    cfnlite properties for "SecurityGroup". As CFN is pretty strict with
    how properties need to formatted, we need to convert and "validate" our
    cfnlite properties.

    Functionally speaking this is a backtracking algorithm which attempts to
    break the cfnlite property into it's constituents components e.g.
    "securitygroups" -> ["Security", "Groups"]. In order to achieve this we
    give the algorithm a tightly bounded "language" (choices arg) which
    contains all the words that the CFN property can be made up of and we
    gradually break down our cfnlite property till we find all its constituents
    or we mark it as an invalid property and return an empty list.

    :param str property: The property to validate
    :param list[str] choices: list of words to choose from
    :returns: list containing components of of the property, if valid
        else an empty list
    :rtype: list[str]
    """
    # memoize results to speed up the backtracking process
    memo: dict[str, bool] = {}
    # word choices to search
    lang: list[str] = choices + RESOURCE_ATTR
    # list holding matching results
    matches: list[str] = []

    def backtrack(s: str, memo: dict[str, bool]) -> bool:
        """Break down word into its constituents using backtracking.

        :param str s: string to look for
        :param dict memo: dict to memoize results and seep up
            backtracking
        :returns: True if s is a property
        :rtype: bool
        """
        # base cases
        if s in memo:
            return memo[s]

        if s == "":
            return True

        res: bool = False
        for word in lang:
            # check if this word matches our property
            match: bool = (
                s.startswith(word.lower())
                and backtrack(s[len(word):], memo)
            )

            if not match:
                continue

            matches.append(word)
            res = True
            break

        memo[s] = res
        return res

    backtrack(property.lower(), memo)
    return matches[::-1]


def nested_find(mapping: dict[KeyType, Any], search_key: KeyType) -> Any | None:
    """Recursively search for a given key in a nested json type object.

    :param dict mapping: the dict to search
    :param KeyType search_key: the key to search for
    :returns: The value associated with the key, if found, else None
    :rtype: Any | None
    """
    if search_key in mapping:
        return mapping[search_key]

    for value in mapping.values():

        if isinstance(value, dict):
            return nested_find(value, search_key)

        if isinstance(value, list) and len(value) > 0:
            for item in value:
                if isinstance(item, dict):
                    # we want to look through all the possibilities to find
                    # our key
                    result: Any = nested_find(item, search_key)

                    if result:
                        return result

    return None


def nested_update(
    mapping: dict[KeyType, Any],
    update_key: KeyType,
    update_value: Any,
) -> dict[KeyType, Any]:
    """Deep update of a nested dict e.g. JSON.

    :param dict mapping: The dict to update
    :param KeyType update_key: The key to update
    :param Any update_value: The new value for the key

    :returns: The updated dict
    :rtype: dict[KeyType, Any]
    """
    if update_key in mapping:
        mapping[update_key] = update_value
        return mapping

    for _, value in mapping.items():

        if isinstance(value, dict):
            nested_update(value, update_key, update_value)

        if isinstance(value, list) and len(value) > 0:
            # this will update all matching values in any dict in the list
            for item in value:
                if isinstance(item, dict):
                    nested_update(item, update_key, update_value)
    return mapping


def clean(
    mapping: dict[KeyType, Any],
    keep_set: set[str],
) -> dict[KeyType, Any]:
    """Clean mapping.

    Remove any keys in the mapping that are not in the keep_set.

    :param dict mapping: The object to clean
    :param set keep_set: field to keep
    :returns: a new object containing fields to keep
    :rtype: dict
    """
    new_mapping: dict[KeyType, Any] = {}
    for key, value in mapping.items():
        if key.lower() not in keep_set:
            continue

        new_mapping[key] = value

    return new_mapping


def create_lang(prop_names: list[str]) -> list[str]:
    """Create the 'language' for parameter resolution.

    "Language" is a misnomer but essentially in order to allow users to not
    need to strictly adhere to the PascalCase required by CNF we need to be
    able to recreate the correct form for each property. The output of this
    function is a list that holds all the words that can be combined together
    to make up any allowed property name for each resource.

    Note, each resource has its own language as there is overlap between
    resource property names but they are combined in resource specific ways.

    The main idea here is to feed a list of all standard property names, in
    PascalCase, to the function which will then split the words into their
    constituent parts e.g.
    SecurityGroupIngress -> ["Security", "Group", "Ingress"].

    The resulting list is then fed into our "resolver" functionality which
    spits out the the correct cased property name. As a result,
    properties must still be spelt correctly, however, any casing combination
    is allowed.

    :param list[str] prop_names: list of the resource property names, as
        defined by AWS
    :returns: list containing property name constituents
    :rtype: list[str]
    """
    # ensure we do not have any duplicates
    lang = set()

    for prop in prop_names:
        # holds a single word during each iteration
        word = []
        for char in prop:
            # if the word is not a capital, add it to word list and carry on
            if not 65 <= ord(char) < 91:
                word.append(char)
                continue

            if word:
                # we've found a new word
                lang.add("".join(word))

            # start new word
            word = [char]

        # get last word in property name
        if word:
            lang.add("".join(word))

    return list(lang)
