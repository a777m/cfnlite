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


def _vpc():
    """Mock VPC yaml definition."""
    vpc = """
    resources:
      vpc:
        cidrBlock: 10.0.0.0/16
    """
    yaml=YAML()
    block = yaml.load(vpc)
    return block


def test_vpc_build__happy():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    vpc = _vpc()

    cfnlite.vpc.build("testVPC", callbacks, vpc["resources"]["vpc"])

    expected = {
        "Resources": {
            "testVPC": {
                "Properties": {
                    "CidrBlock": "10.0.0.0/16",
                },
                "Type": "AWS::EC2::VPC",
            }
        }
    }

    assert template.to_dict() == expected


def test_vpc_build__tags():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    vpc = _vpc()

    # add tags
    tags = {"tag1": "value1", "tag2": "value2"}
    vpc["resources"]["vpc"]["tags"] = tags

    cfnlite.vpc.build("testVPC", callbacks, vpc["resources"]["vpc"])

    expected = {
        "Resources": {
            "testVPC": {
                "Properties": {
                    "CidrBlock": "10.0.0.0/16",
                    "Tags": [
                        {"Key": "default-cfnlite-resource-name", "Value": "testVPC"},
                        {"Key": "tag1", "Value": "value1"},
                        {"Key": "tag2", "Value": "value2"},
                    ],
                },
                "Type": "AWS::EC2::VPC",
            }
        }
    }

    assert template.to_dict() == expected


def test_vpc_build__references():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    vpc = _vpc()

    # create security group for reference
    sg = troposphere.ec2.SecurityGroup(
        "TestSecurityGroupsName",
        GroupDescription="aFakeGroupID",
        SecurityGroupIngress=[],
    )

    # add to template and symbol table
    callbacks["add_resource"](sg)
    callbacks["add_symbol"]("securitygroups", sg)

    # add ref
    vpc["resources"]["vpc"]["dependsOn"] = "ref! securitygroups"

    cfnlite.vpc.build("testVPC", callbacks, vpc["resources"]["vpc"])

    expected = {
        "Resources": {
            "TestSecurityGroupsName": {
                "Properties": {
                    "GroupDescription": "aFakeGroupID",
                    "SecurityGroupIngress": [],
                },
                "Type": "AWS::EC2::SecurityGroup",
            },
            "testVPC": {
                "DependsOn": {"Ref": "TestSecurityGroupsName"},
                "Properties": {
                    "CidrBlock": "10.0.0.0/16",
                },
                "Type": "AWS::EC2::VPC",
            }
        }
    }

    assert template.to_dict() == expected


@pytest.mark.parametrize("key,value", [
    ("EnableDnsHostnames", True),
    ("EnableDnsSupport", True),
    ("InstanceTenancy", "default"),
    ("Ipv4IpamPoolId", "ipv4-pool-id"),
    ("Ipv4NetmaskLength", 50),
])
def test_vpc_build__all_possible_props(key, value):
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    vpc = _vpc()
    # add values
    vpc["resources"]["vpc"][key.lower()] = value

    cfnlite.vpc.build("testVPC", callbacks, vpc["resources"]["vpc"])

    expected = {
        "Resources": {
            "testVPC": {
                "Properties": {
                    "CidrBlock": "10.0.0.0/16",
                    key: value,
                },
                "Type": "AWS::EC2::VPC",
            }
        }
    }

    assert template.to_dict() == expected
