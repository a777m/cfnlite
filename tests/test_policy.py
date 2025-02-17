"""Tests for Policies."""

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


def _policy():
    """Simple mock policy definition."""

    policy = """
    resources:
      policy:
        policyName: test policy
        statement:
          - action: 'cloudwatch:*'
    """
    yaml = YAML()
    block = yaml.load(policy)
    return block


def test_policy_build__happy():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    policy = _policy()

    cfnlite.policy.build("testPolicy", callbacks, policy["resources"]["policy"])

    expected = {
        "Resources": {
            "testPolicy": {
                "Properties": {
                    "PolicyName": "test policy",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["cloudwatch:*"],
                                "Resources": ["*"],
                            },
                        ],
                    },
                },
                "Type": "AWS::IAM::Policy",
            },
        },
    }

    assert template.to_dict() == expected


def test_policy_build__make_effect_deny():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    policy = _policy()

    # add effect = deny
    deny_statement = {"action": "dynamodb:*", "effect": "Deny"}
    policy["resources"]["policy"]["statement"].append(deny_statement)

    cfnlite.policy.build("testPolicy", callbacks, policy["resources"]["policy"])

    expected = {
        "Resources": {
            "testPolicy": {
                "Properties": {
                    "PolicyName": "test policy",
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
                                "Action": ["dynamodb:*"],
                                "Resources": ["*"],
                            },
                        ],
                    },
                },
                "Type": "AWS::IAM::Policy",
            },
        },
    }

    assert template.to_dict() == expected


def test_policy_build__add_specific_resources():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    policy = _policy()

    # add effect = deny
    deny_statement = {
        "action": "sns:*",
        "effect": "Deny",
        "resources": "dynamodb:*"
    }
    policy["resources"]["policy"]["statement"].append(deny_statement)

    cfnlite.policy.build("testPolicy", callbacks, policy["resources"]["policy"])

    expected = {
        "Resources": {
            "testPolicy": {
                "Properties": {
                    "PolicyName": "test policy",
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
                                "Action": ["sns:*"],
                                "Resources": ["dynamodb:*"],
                            },
                        ],
                    },
                },
                "Type": "AWS::IAM::Policy",
            },
        },
    }

    assert template.to_dict() == expected


def test_policy_build__pass_all_possible_policy_properties():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    policy = _policy()

    policy["resources"]["policy"]["groups"] = "fake-group"
    policy["resources"]["policy"]["roles"] = "fake-role"
    policy["resources"]["policy"]["users"] = "fake-user"

    # add a resource attribute value
    policy["resources"]["policy"]["dependson"] = "test-depends-on"

    cfnlite.policy.build("testPolicy", callbacks, policy["resources"]["policy"])

    expected = {
        "Resources": {
            "testPolicy": {
                "DependsOn": "test-depends-on",
                "Properties": {
                    "Groups": ["fake-group"],
                    "PolicyName": "test policy",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["cloudwatch:*"],
                                "Resources": ["*"],
                            },
                        ],
                    },
                    "Roles": ["fake-role"],
                    "Users": ["fake-user"],
                },
                "Type": "AWS::IAM::Policy",
            },
        },
    }

    assert template.to_dict() == expected


def test_policy_build__pass_all_possible_statement_properties():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    policy = _policy()

    # add principal and sid
    statement = policy["resources"]["policy"]["statement"][0]
    statement["sid"] = "test Sid"
    statement["principal"] = {"aKey": "aValue"}

    cfnlite.policy.build("testPolicy", callbacks, policy["resources"]["policy"])

    expected = {
        "Resources": {
            "testPolicy": {
                "Properties": {
                    "PolicyName": "test policy",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["cloudwatch:*"],
                                "Resources": ["*"],
                                "Principal": {"aKey": "aValue"},
                                "Sid": "test Sid",
                            },
                        ],
                    },
                },
                "Type": "AWS::IAM::Policy",
            },
        },
    }

    assert template.to_dict() == expected


def test_policy_build__with_reference():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    policy = _policy()

    role = troposphere.iam.Role("TestRole", AssumeRolePolicyDocument={})
    callbacks["add_resource"](role)
    callbacks["add_symbol"]("role", role)

    # add principal and sid
    policy["resources"]["policy"]["roles"] = "ref! role"

    cfnlite.policy.build("testPolicy", callbacks, policy["resources"]["policy"])

    expected = {
        "Resources": {
            "TestRole": {
                "Properties": {
                    "AssumeRolePolicyDocument": {},
                },
                "Type": "AWS::IAM::Role",
            },
            "testPolicy": {
                "Properties": {
                    "PolicyName": "test policy",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["cloudwatch:*"],
                                "Resources": ["*"],
                            },
                        ],
                    },
                    "Roles": [{"Ref": "TestRole"}],
                },
                "Type": "AWS::IAM::Policy",
            },
        },
    }

    assert template.to_dict() == expected


def test_policy_build__add_duplicate_policy_prop():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    policy = _policy()

    policy["resources"]["policy"]["PolicyName"] = "I am a duplicate"

    with pytest.raises(ValueError) as e:
        cfnlite.policy.build(
            "testPolicy", callbacks, policy["resources"]["policy"])

    assert str(e.value) == (
        "Each property can only be used once. "
        "Offending prop: PolicyName")


def test_policy_build__add_duplicate_statement_prop():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    policy = _policy()

    # add duplicate action
    statement = policy["resources"]["policy"]["statement"][0]
    statement["aCtion"] = "duplicate Action"

    with pytest.raises(ValueError) as e:
        cfnlite.policy.build(
            "testPolicy", callbacks, policy["resources"]["policy"])

    assert str(e.value) == (
        "Statement properties can only be defined once. "
        "Offending key: aCtion")


@pytest.mark.parametrize("bad_prop",
    ["iAmFake", "fake-with-dash", "fake with space"]
)
def test_policy_build__bad_prop(bad_prop):
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    policy = _policy()

    # add fake property to policy
    policy["resources"]["policy"][bad_prop] = "FakeValue"

    with pytest.raises(ValueError) as e:
        cfnlite.policy.build(
            "testPolicy", callbacks, policy["resources"]["policy"])

    assert str(e.value) == f"'{bad_prop}' is an invalid attribute for Policies"
