"""Generate a CloudFormation from a cfnlite file."""

import argparse
import pathlib
import sys
from typing import Any, Callable, TypedDict

from ruamel.yaml import YAML
import troposphere

import cfnlite
from cfnlite import lib


# Callbacks type, just to sure things up for people with cool IDEs
class CallBacks(TypedDict):
    """Types for each of the callback function signatures."""

    add_symbol: Callable[[str, Any], None]
    get_symbol: Callable[[str], Any]
    add_resource: Callable[[Any], None]


# This holds references to each resource that has been created via its name
# the reason we need this is to resolve dependencies between the resources
# i.e. if a resource needs to !Ref another resource, it can look in here
SYMBOL_TABLE: dict[str, object | None] = {}


# We're going to have a uniform "dispatch" function for each supported resource
# type. this is to minimise the need for custom logic for each resource.
# As such, we only need to hold a reference to each resources module, which
# is then used to call the dispatch function.
#
# Re dispatch functions, each module should be named after a corresponding
# aws resource and should define two functions: `build` and `explain`.
# - `build` does what it says on the tin and builds the CFN for the resource.
# - `explain` prints out the properties we support for each resource.
DISPATCH: dict[str, Callable] = {
    "ec2": cfnlite.ec2,
    "policy": cfnlite.policy,
    "role": cfnlite.role,
    "securitygroups": cfnlite.securitygroups,
}

# global CloudFormation template, contains what will eventually be generated
TEMPLATE: troposphere.Template = troposphere.Template()

# for making the resource type checking more readable
Resources = dict[str, Any]


def write_to_file(
    filepath: pathlib.Path,
    template: troposphere.Template,
) -> None:
    """Write CloudFormation to a file.

    Note: this is distructive, we always overwrite the contents of the
    destination file.

    :param pathlib.Path filepath: the path to the destination file
    :param troposphere.Template template: the template to dump
    """
    with open(filepath, "w") as fd:  # pylint: disable=unspecified-encoding
        fd.write(template.to_yaml())


def add_symbol(resource: str, ref: Any) -> None:
    """Add a resource to the symbol table.

    :param str resource: The name of the resource
    :param Any ref: a reference to a resource
    """
    SYMBOL_TABLE[resource] = ref


def get_symbol(resource: str) -> Any:
    """Get a resource reference from the symbol table.

    :param str resource: name of the resource to fetch
    """
    # Note: we're purposefully not checking, as we want this to blow up for
    # (un)known/defined resources
    return SYMBOL_TABLE[resource]


def add_resource(resource: Any) -> None:
    """Add a resource to the template.

    :param Any resource: reference to the resource to add
    """
    # This assumes a global template object exists
    TEMPLATE.add_resource(resource)


def _init_symbol_table(resources: Resources) -> None:
    """Initialise the symbol table for incoming resources.

    'incoming' here means any resources defined in the CFNLite file.

    :param Resources resource: a dict containing all resources that
        will be created by CFNLite
    :raises ValueError: if resource is unsupported
    """
    for resource in resources.keys():
        # check if resource is unsupported
        if resource.lower() not in DISPATCH:
            raise ValueError(f"{resource} is unsupported to spelt wrong")

        SYMBOL_TABLE[resource.lower()] = None


def _init_callbacks_table() -> CallBacks:
    """Initialise callbacks table.

    Callbacks are used to allow "child" modules to access external
    functionality e.g. getting a resource from the symbol table. This serves a
    few purposes; firstly, this central modules does not need to do more than
    the bare minimum when it comes to orchestrating between different child
    modules, especially when one module depends on another i.e. Refs.
    Secondly, we can defer the real "work" to the callee's. This means that
    this modules does not need to know if or what the callee is adding to the
    template, what the symbols in the table are called etc, this is
    particularly useful when the callee is creating resources in a loop.
    And lastly, this approach saves us from having to pass around giant objects
    which contain the current state of the program.
    """
    callbacks: CallBacks = {
        "add_symbol": add_symbol,
        "get_symbol": get_symbol,
        "add_resource": add_resource,
    }

    return callbacks


def processing_order(resources: Resources) -> list[str]:
    """Calculate the processing order of the cfnlite file.

    This function basically figures out the dependency order of the
    resources in the cfnlite file and returns the preferred order.

    :param Resources resources: object containing all resources which will
        be created by cnflite
    :return: A list sorted in the order that resources need to be main in
        with respect to any dependencies between the resources.
    :rtype: list[str]
    """
    # an adjacency list representation of the graph
    graph: dict[str, list[str]] = lib.dep_graph(resources)
    return lib.topological_sort(graph)


def parse(cfnlite_file: pathlib.Path):
    """Parse a cfnlite file.

    :param pathlib.Path cfnlite_file: a cfnlite file to parse
    :raises ValueError: if a resource in cfnlite file is unsupported or the
        file has no name
    """
    yaml = YAML()
    doc: dict[str, Any] = yaml.load(cfnlite_file)

    if not doc["name"]:
        raise ValueError("A CNFLite file must have a name field")

    # init symbol table
    _init_symbol_table(doc["resources"])

    callbacks = _init_callbacks_table()

    # build dep graph
    order: list[str] = processing_order(doc["resources"])

    for resource in order:
        if resource.lower() not in DISPATCH:
            raise ValueError(f"{resource} not supported")

        name = f"{doc['name']}{resource.upper()}"
        DISPATCH[resource.lower()].build(
            name,
            callbacks,
            doc["resources"][resource]
        )


def main(args: argparse.Namespace) -> int:
    """Main function.

    :param argparse.Namespace args: CLI arguments
    :returns: 0 if successfully parsed else 1
    :rtype: int
    """
    if args.output_file and args.dry_run:
        raise ValueError(
            "Either print to console or write to a file, not both.")

    if not args.file.exists():
        raise ValueError(f"File at path not found: {args.file}")

    if args.explain:
        if args.explain.lower() == "resources":
            DISPATCH.keys()

        elif args.explain.lower() in DISPATCH:
            DISPATCH[args.explain.lower()].explain()

        else:
            raise ValueError(f"'{args.explain}' is not a valid resource type.")

        return 0

    # optimistically attempt to parse file, if there are exceptions
    # they will be handled higher up the stack
    parse(args.file)

    if args.dry_run:
        print(TEMPLATE.to_yaml())

    if args.output_file:
        write_to_file(args.output_file, TEMPLATE)

    return 0


def cli() -> argparse.Namespace:
    """Parse command line arguments

    :return: parsed CLI args
    :rtype: argsparse.Namespace
    """
    parser = argparse.ArgumentParser(
        prog="cfnlite", description="cfnlite CloudFormation generator")

    parser.add_argument(
        "file",
        type=pathlib.Path,
        help="A YAML cfnlite file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated CNF template to console"
    )
    parser.add_argument(
        "--output-file",
        type=pathlib.Path,
        help="File to write resulting CloudFormation to"
    )
    parser.add_argument(
        "--explain",
        help="Use keyword 'resources' to show a list of supported resources "
             "or use <resource-name> to show a list of supported properties "
             "for the selected resource type"
    )
    return parser.parse_args()


if __name__ == "__main__":
    cli_incoming = cli()
    build_exit = 0

    try:
        main(cli_incoming)
    except Exception as error:  # pylint: disable=broad-exception-caught
        print(str(error))
        build_exit = 1

    sys.exit(build_exit)
