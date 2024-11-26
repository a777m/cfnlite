"""Testing cfnlite utility functions."""

import pytest

from cfnlite.lib import utils

# example "language" array, these are the words associated with EC2 params
# we'll just use them here for testing purposes, there is nothing special their
# selection
LANG = [
    'Additional', 'Address', 'Affinity', 'Api', 'Arn', 'Availability',
    'Behavior', 'Block', 'Device', 'Disable', 'Ebs', 'Group', 'Groups', 'Host',
    'Iam', 'Id', 'Ids', 'Image', 'Info', 'Initiated', 'Instance', 'Interfaces',
    'Ip', 'Kernel', 'Key', 'Mappings', 'Monitoring', 'Name', 'Network',
    'Optimized', 'Placement', 'Private', 'Profile', 'Resource', 'Security',
    'Shutdown', 'Subnet', 'Tenancy', 'Termination', 'Type', 'Volumes', 'Zone'
]


def nested_object():
    """A mock nested object."""
    # this mock uses an example policy as it is a good example usecase for our
    # needs i.e. the kind of nesting we are likely to see in CNF templates
    mock_obj = {
        "testPolicy": {
            "Properties": {
                "PolicyName": "test policy",
                "PolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "ExampleStatement",
                            "Effect": "Allow",
                            "Action": ["cloudwatch:*"],
                            "Resources": ["*"],
                        },
                        {
                            "Sid": "ExampleStatement",
                            "Effect": "Deny",
                            "Action": ["sns:*"],
                            "Resources": ["dynamodb:*"],
                        },
                    ],
                },
                "Roles": [],
            },
            "Type": "AWS::IAM::Policy",
        },
    }

    return mock_obj


@pytest.mark.parametrize("word,expected",
    [
        ("Additional", ["Additional"]),
        ("InstanceInitiatedShutdownBehavior", ["Instance", "Initiated", "Shutdown", "Behavior"]),
        ("securitygroups", ["Security", "Groups"]),
        ("SECURITYGROUPS", ["Security", "Groups"]),
        ("secuRITYgroups", ["Security", "Groups"]),
        ("secuRITYGRoups", ["Security", "Groups"]),
        ("SECURITYgroups", ["Security", "Groups"]),
        ("SECURITYgroups", ["Security", "Groups"]),
        ("kernelID", ["Kernel", "Id"]),
        # bad spelling
        ("SecurtyGroup", []),
        ("Security Group", []),
        ("Security-Group", []),
        ("iDoNotExist", []),

    ])
def test_param_validator__all_lowercase(word, expected):
    assert utils.property_validator(word, LANG) == expected


@pytest.mark.parametrize("key,expected", [
    # happy cases
    ("Type", "AWS::IAM::Policy"),
    ("Version", "2012-10-17"),
    ("Roles", []),
    ("PolicyName", "test policy"),
    # keys in lists will return the first matching key found
    ("Sid", "ExampleStatement"),
    ("Effect", "Allow"),
    ("Action", ["cloudwatch:*"]),
    ("Resources", ["*"]),
    # unhappy cases
    ("type", None),
    ("Vsion", None),
    ("Role", None),
    ("id", None),
    ("Effects", None),
    ("Resource", None),
    ("IdoNotExist", None),
])
def test_nested_find__simple_keys(key, expected):
    mock_nested_obj = nested_object()
    assert utils.nested_find(mock_nested_obj, key) == expected


def test_nested_find__complex_object():
    """Get the statement list from the mock object."""
    mock_nested_obj = nested_object()

    expected =[
        {
            "Sid": "ExampleStatement",
            "Effect": "Allow",
            "Action": ["cloudwatch:*"],
            "Resources": ["*"],
        },
        {
            "Sid": "ExampleStatement",
            "Effect": "Deny",
            "Action": ["sns:*"],
            "Resources": ["dynamodb:*"],
        },
    ]

    assert utils.nested_find(mock_nested_obj, "Statement") == expected


@pytest.mark.parametrize("key,old_value,new_value", [
    ("Type", "AWS::IAM::Policy", "AWS::IAM::EC2"),
    ("Version", "2012-10-17", "2012-10-20"),
    ("Roles", [], ["some-role"]),
    ("PolicyName", "test policy", "updated test policy"),
])
def test_nested_update__simple_keys(key, old_value, new_value):
    mock_nested_obj = nested_object()
    # ensure old value is initially set
    assert utils.nested_find(mock_nested_obj, key) == old_value
    # update and check again
    updated = utils.nested_update(mock_nested_obj, key, new_value)
    assert utils.nested_find(updated, key) == new_value


def test_nested_update__value_in_list():
    """Update a value in a dict which lives in a list."""
    mock_nested_obj = nested_object()
    # update the sid value
    updated = utils.nested_update(mock_nested_obj, "Sid", "NewSidFromTest")

    expected =[
        {
            "Sid": "NewSidFromTest",
            "Effect": "Allow",
            "Action": ["cloudwatch:*"],
            "Resources": ["*"],
        },
        {
            "Sid": "NewSidFromTest",
            "Effect": "Deny",
            "Action": ["sns:*"],
            "Resources": ["dynamodb:*"],
        },
    ]

    assert utils.nested_find(mock_nested_obj, "Statement") == expected


def test_nested_update__nothing_changes_if_key_not_found():
    mock_nested_obj = nested_object()
    # update the fake value
    updated = utils.nested_update(nested_object(), "IdontExist", "fakeval")
    # make sure nothing changed
    assert updated == nested_object()
