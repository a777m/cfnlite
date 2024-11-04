import pytest
from ruamel.yaml import YAML

from cfnlite.lib import deps


def _graph():
    graph = {
        'ec2': {
            'InstanceType': 't2.micro',
            'ImageId': 'ami-0b45ae66668865cd6',
        },
        's3': {
            'BucketName': 'item',
            'with': ['name1', 'name2', 'name3']
        },
        'securitygroups': {
            'ingress': ['http', 'ssh', 'icmp'],
            'egress': ['http', 'ssh', 'icmp']
        }
    }

    return graph


def test_dep_tree__no_deps():
    graph = _graph()
    actual = deps.dep_graph(graph)

    expected = {
        "ec2": [],
        "securitygroups": [],
        "s3": [],
    }

    assert actual == expected


def test_dep_tree__simple_ref():
    graph = _graph()
    # add some simple deps
    graph["ec2"]["SecurityGroups"] = 'ref securitygroups'
    graph["s3"]["SecurityGroups"] = 'ref ec2'

    actual = deps.dep_graph(graph)

    expected_graph = {
        "ec2": ["securitygroups"],
        "securitygroups": [],
        "s3": ["ec2"],
    }

    assert actual == expected_graph


def test_dep_tree__self_ref():
    graph = _graph()
    # add some simple deps
    graph["ec2"]["SecurityGroups"] = 'ref ec2'
    graph["s3"]["SecurityGroups"] = 'ref ec2'

    with pytest.raises(ValueError):
        deps.dep_graph(graph)


def test_dep_tree__nothing_after_ref():
    graph = _graph()
    # add some simple deps
    graph["ec2"]["SecurityGroups"] = 'ref'
    graph["s3"]["SecurityGroups"] = 'ref ec2'

    with pytest.raises(ValueError):
        deps.dep_graph(graph)


def test_dep_tree__too_many_values_after_ref():
    graph = _graph()
    # add some simple deps
    graph["ec2"]["SecurityGroups"] = 'ref ec2 securitygroups'

    with pytest.raises(ValueError):
        deps.dep_graph(graph)


def test_dep_tree__ref_pointing_undefined_resource():
    graph = _graph()
    # add some simple deps
    graph["ec2"]["SecurityGroups"] = 'ref ec3'

    with pytest.raises(ValueError) as err_msg:
        deps.dep_graph(graph)
    
    assert str(err_msg.value) == "Undefined resource: ec3"


def test_dep_tree__has_cycle():
    graph = _graph()
    # add some a simple cycle
    graph["ec2"]["SecurityGroups"] = 'ref securitygroups'
    graph["ec2"]["AnotherOne"] = 'ref s3'
    graph["s3"]["SecurityGroups"] = 'ref ec2'

    with pytest.raises(ValueError):
        actual = deps.dep_graph(graph)


def test_top_sort__no_deps():
    graph = _graph()
    actual = deps.dep_graph(graph)

    t_sort = deps.topological_sort(actual)


    # order can be anything so does not matter here but we need to make sure
    # all resources have been found
    assert len(t_sort) == len(graph)


def test_top_sort__simple_deps():
    graph = _graph()
    # add some simple deps
    graph["ec2"]["SecurityGroups"] = 'ref securitygroups'
    graph["s3"]["SecurityGroups"] = 'ref ec2'

    graph = deps.dep_graph(graph)

    # in our graph our dependancies go:
    # s3 depends on ec2 , ec2 depends on security groups, security groups depend
    # on nothing i.e. s2 -> ec2 -> securitygroups - so our order is the
    # reverse of this
    expected = ["securitygroups", "ec2", "s3"]

    actual = deps.topological_sort(graph)

    assert actual == expected


def test_top_sort__cycle():
    # "graph" with a cycle
    cycle = {
        "ec2": ["securitygroups"],
        "securitygroups": ["ec2"],
        "s3": ["ec2"],
    }

    with pytest.raises(ValueError):
        deps.topological_sort(cycle)


def test_deps__end_to_end():
    """This test simulates input coming from actual yaml."""
    t = """
    name: TestTroposphereTing
    resources:
      ec2:
        InstanceType: t2.micro
        ImageId: ami-0b45ae66668865cd6
        SecurityGroups: ref securitygroups
      s3:
        BucketName: item
        SecurityGroups: ref ec2
        with:
          - name1
          - name2
          - name3
      securitygroups:
        ingress: [http, ssh, icmp]
        egress: [http, ssh, icmp]
    """
    yaml=YAML()
    block = yaml.load(t)

    actual = deps.dep_graph(block["resources"])

    expected_graph = {
        "ec2": ["securitygroups"],
        "securitygroups": [],
        "s3": ["ec2"],
    }

    assert actual == expected_graph

    # ensure sorting is correct
    assert deps.topological_sort(expected_graph) == \
        ["securitygroups", "ec2", "s3"]
