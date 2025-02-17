import pytest

import troposphere

from cfnlite.lib import tags


def mock_callbacks(template):
    """Mock out the callbacks object."""
    symbols = {}
    def get_symbol(ref):
        return symbols[ref]

    def add_symbol(resource, ref):
        symbols[resource] = ref

    def add_resource(resource):
        template.add_resource(resource)

    return {
        "add_symbol": add_symbol,
        "get_symbol": get_symbol,
        "add_resource": add_resource,
    }


def test_tags__happy():
    # this is needed because in real scenarios, the ref resolution needs
    # the callbacks
    template = troposphere.Template()
    callbacks = mock_callbacks(template)["get_symbol"]

    input_tags = {"tag1": "value1", "tag2": "value2"}

    expected = [
        {"Key": "default-cfnlite-resource-name", "Value": "test-tag"},
        {"Key": "tag1", "Value": "value1"},
        {"Key": "tag2", "Value": "value2"},
    ]

    assert tags.add_tags("test-tag", input_tags, callbacks).to_dict() == expected


def test_tags__with_refs():
    # setup
    template = troposphere.Template()
    callbacks = mock_callbacks(template)

    # create security group reference
    sg = troposphere.ec2.SecurityGroup(
        "TestSecurityGroupsName", GroupDescription="aFakeGroupID")

    # add to template and symbol table
    callbacks["add_resource"](sg)
    callbacks["add_symbol"]("securitygroups", sg)

    input_tags = {
        "tag1": "value1",
        "tag2": "value2",
        "sg": "ref! securitygroups"
    }

    expected = [
        {"Key": "default-cfnlite-resource-name", "Value": "test-tag"},
        {"Key": "sg", "Value": {"Ref": "TestSecurityGroupsName"}},
        {"Key": "tag1", "Value": "value1"},
        {"Key": "tag2", "Value": "value2"},
    ]

    cb = callbacks["get_symbol"]
    assert tags.add_tags("test-tag", input_tags, cb).to_dict() == expected
