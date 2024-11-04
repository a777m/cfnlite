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
