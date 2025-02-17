"""Handle CFN tag generation."""

import troposphere

from cfnlite.lib import validators


def add_tags(
    name: str,
    tags: dict[str, str],
    callback: validators.GetSymbolCallable,
) -> troposphere.Tags:
    """Generate CFN tags.

    :param str name: name of resource tags belong to
    :param dict tags: dict containing the tag key/value pairs
    :param validators.GetSymbolCallable callback: the get_symbol callback

    :returns: a troposphere tags object
    :rtype: troposphere.Tags
    """
    new_tags_mapping: dict[str, str] = {"default-cfnlite-resource-name": name}

    for key, value in tags.items():
        if (isinstance(value, str) and value.strip().startswith("ref!")):
            # pylint: disable=protected-access
            # The reason we do this protected access to is prevent circular
            # dependencies if we put this function in utils (validators also
            # import utils) and it does not make sense to put his function in
            # the validators module
            value = validators._handle_refs(value, callback)

        new_tags_mapping[key] = value
    return troposphere.Tags(**new_tags_mapping)
