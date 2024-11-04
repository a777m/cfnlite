"""cfnlite utilities."""

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
