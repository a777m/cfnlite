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
