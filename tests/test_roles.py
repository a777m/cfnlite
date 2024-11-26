"""Tests for Roles."""

import pytest
from ruamel.yaml import YAML
import troposphere

import cfnlite


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


def _role():
    """Mock role definition."""
    role = """
    resources:
      role:
        AssumeRolePolicyDocument:
          Principal:
            service: 'ec2.amazonaws.com'
          Action:
            - 'sts:AssumeRole'
    """
    yaml = YAML()
    block = yaml.load(role)
    return block


def test_role_build__happy():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    role = _role()

    cfnlite.role.build("testRole", callbacks, role["resources"]["role"])

    expected = {
        "Resources": {
            "testRole": {
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "PolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Action": ["sts:AssumeRole"],
                                    "Effect": "Allow",
                                    "Principal": {
                                        "service": "ec2.amazonaws.com"
                                    },
                                    "Resources": ["*"],
                            }],
                        },
                    },
                    "RoleName": "TestRole"
                },
                "Type": "AWS::IAM::Role"
            },
        },
    }

    assert template.to_dict() == expected


def test_role_build__add_inline_policies():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    role = _role()

    # add policies
    role["resources"]["role"]["policies"] = [
        {"Action": "cloudwatch:*"}, {"Action": "lakeformation:*"}]

    cfnlite.role.build("testRole", callbacks, role["resources"]["role"])

    expected = {
        "Resources": {
            "testRole": {
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "PolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Action": ["sts:AssumeRole"],
                                    "Effect": "Allow",
                                    "Principal": {
                                        "service": "ec2.amazonaws.com"
                                    },
                                    "Resources": ["*"],
                            }],
                        },
                    },
                    "Policies": [
                        {
                            "PolicyName": "Example cfnlite policy",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": ["cloudwatch:*"],
                                        "Resources": ["*"],
                                    },
                                    {
                                        "Effect": "Allow",
                                        "Action": ["lakeformation:*"],
                                        "Resources": ["*"],
                                    },
                                ],
                            },
                        },
                    ],
                    "RoleName": "TestRole",
                },
                "Type": "AWS::IAM::Role",
            },
        },
    }

    assert template.to_dict() == expected


def test_role_build__apd_effect_deny():
    """Change assume policy document effect to deny."""
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    role = _role()

    # change APD effect to deny
    role["resources"]["role"]["AssumeRolePolicyDocument"].update({"effect": "Deny"})

    cfnlite.role.build("testRole", callbacks, role["resources"]["role"])

    expected = {
        "Resources": {
            "testRole": {
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "PolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Action": ["sts:AssumeRole"],
                                    "Effect": "Deny",
                                    "Principal": {
                                        "service": "ec2.amazonaws.com"
                                    },
                                    "Resources": ["*"],
                            }],
                        },
                    },
                    "RoleName": "TestRole"
                },
                "Type": "AWS::IAM::Role"
            },
        },
    }

    assert template.to_dict() == expected


def test_role_build__inline_policy_effect_deny():
    """Change the inline policy effect to deny."""
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    role = _role()

    # add policies
    role["resources"]["role"]["policies"] = [
        {"Action": "cloudwatch:*"}, {"Action": "lakeformation:*", "effect": "Deny"}]

    cfnlite.role.build("testRole", callbacks, role["resources"]["role"])

    expected = {
        "Resources": {
            "testRole": {
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "PolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Action": ["sts:AssumeRole"],
                                    "Effect": "Allow",
                                    "Principal": {
                                        "service": "ec2.amazonaws.com"
                                    },
                                    "Resources": ["*"],
                            }],
                        },
                    },
                    "Policies": [
                        {
                            "PolicyName": "Example cfnlite policy",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": ["cloudwatch:*"],
                                        "Resources": ["*"],
                                    },
                                    {
                                        "Effect": "Deny",
                                        "Action": ["lakeformation:*"],
                                        "Resources": ["*"],
                                    },
                                ],
                            },
                        },
                    ],
                    "RoleName": "TestRole",
                },
                "Type": "AWS::IAM::Role",
            },
        },
    }

    assert template.to_dict() == expected


def test_role_build__pass_all_possible_role_properties():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    role = _role()

    role["resources"]["role"]["description"] = "Test description"
    role["resources"]["role"]["maxsessionduration"] = 10
    role["resources"]["role"]["path"] = "/"
    role["resources"]["role"]["permissionsboundary"] = "fake-boundary"

    cfnlite.role.build("testRole", callbacks, role["resources"]["role"])

    expected = {
        "Resources": {
            "testRole": {
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "PolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Action": ["sts:AssumeRole"],
                                    "Effect": "Allow",
                                    "Principal": {
                                        "service": "ec2.amazonaws.com"
                                    },
                                    "Resources": ["*"],
                            }],
                        },
                    },
                    "Description": "Test description",
                    "MaxSessionDuration": 10,
                    "Path": "/",
                    "PermissionsBoundary": "fake-boundary",
                    "RoleName": "TestRole",
                },
                "Type": "AWS::IAM::Role"
            },
        },
    }

    assert template.to_dict() == expected


def test_role_build__add_duplicate_role_property():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    role = _role()

    role["resources"]["role"]["assumeRolePolicyDocument"] = "I am duplicate"

    with pytest.raises(ValueError) as e:
        cfnlite.role.build("testRole", callbacks, role["resources"]["role"])


    assert str(e.value) == (
        "Each property can only be used once. "
        "Offending prop: assumeRolePolicyDocument")


def test_role_build__add_duplicate_statement_property():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    role = _role()

    role["resources"]["role"]["policies"] = [
        {"Action": "fake-action-1", "action": "fake-action-2"}]

    with pytest.raises(ValueError) as e:
        cfnlite.role.build("testRole", callbacks, role["resources"]["role"])


    assert str(e.value) == (
        "Statement properties can only be defined once. "
        "Offending key: action")


@pytest.mark.parametrize("bad_prop",
    ["iAmFake", "fake-with-dash", "fake with space"]
)
def test_role_build__bad_prop(bad_prop):
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    role = _role()

    role["resources"]["role"][bad_prop] = "fakeValue"

    with pytest.raises(ValueError) as e:
        cfnlite.role.build("testRole", callbacks, role["resources"]["role"])

    assert str(e.value) == f"'{bad_prop}' is an invalid attribute for Roles"
