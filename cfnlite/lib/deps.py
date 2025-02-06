"""Build the dependency graph for cfnlite resources."""

from typing import Any

DepGraph = dict[str, list[str]]


def deps(
    name: str,
    resources: dict[str, Any],
    graph: DepGraph,
    visited: set[str],
    path: set[str],
) -> None:
    """Recursively build resource dependencies from a given resource name.

    The resource name acts as the start "node" for our search.

    :param str name: the name of the resource - as defined in the cfnlite
        yaml file.
    :param dict resources: the graph of resources defined in the cfnlite
        yaml file.
    :param DepGraph graph: the dependency graph we're building during each
        iteration of this function.
    :param set[str] visited: a set containing visited resources
    :param set[str] path: a set containing all visited resources on the
        current dfs path.

    :raises ValueError:
    """
    if name in path:
        raise ValueError("There is a cycle!!")

    if name in visited:
        return

    # add resource name to graph if not already present
    graph[name] = graph.get(name, [])

    # helps us find cycles
    path.add(name)
    for value in resources[name].values():
        if not isinstance(value, str) or "ref" not in value.strip().lower():
            continue

        value: list[str] = value.strip().split()

        if len(value) < 2 or len(value) > 2:
            raise ValueError(
                "Keyword 'ref' must be followed by exactly one argument")

        # grab the resource being referenced
        dep: str = value[1]

        # dont silently fail if invalid resource is referenced
        if dep not in resources:
            raise ValueError(f"Undefined resource: {dep}")

        # recurse on all dependent resources
        deps(dep, resources, graph, visited, path)

        graph[name].append(dep)

    path.remove(name)

    # mark current resource as visited
    visited.add(name)


def dep_graph(resources: dict[str, Any]) -> DepGraph:
    """Build dependency graph for all resources in a cnflite file.

    :param dict[str, Any] resources: resources object from a cfnlite
        file
    :return: an adjacency list representing a graph of resource
        dependencies
    :rtype: DepGraph
    """
    graph: DepGraph = {}
    # visited set ensures we dont visit the same resources twice
    visited: set[str] = set()

    for resource in resources:
        if resource not in visited:
            # dfs search from each resource to find all deps
            deps(resource, resources, graph, visited, set())
    return graph


def sorter(
    resource: str,
    graph: DepGraph,
    order: list[str],
    visited: set[str],
    path: set[str]
) -> None:
    """Create the topological sorting from a given resource.

    :param str resource: the name of the resource - as defined in the cfnlite
        yaml file.
    :param DepGraph graph: dependency graph of resources defined in the
        cfnlite yaml file.
    :param lis[str] order: the topological order we're building with each
        iteration of this function.
    :param set[str] visited: a set containing visited resources
    :param set[str] path: a set containing all visited resources on the
        current dfs path.

    :raises ValueError: if there is a cycle
    """

    if resource in path:
        raise ValueError("Cycle found")

    if resource in visited:
        return

    path.add(resource)

    for dep in graph[resource]:
        # recursively build order
        sorter(dep, graph, order, visited, path)

    path.remove(resource)

    visited.add(resource)
    order.append(resource)


def topological_sort(graph: DepGraph) -> list[str]:
    """Return the topological ordering of a given graph.

    :param DepGraph graph: an adjacency list representation of a graph
    :return: the topological order
    :rtype: list[str]
    """
    # holds all explored resources
    visited: set[str] = set()
    # holds the explored resources on the current dfs path
    path: set[str] = set()
    # holds the final topological ordering of the cnflite resources
    order: list[str] = []

    for resource in graph:
        sorter(resource, graph, order, visited, path)

    return order
