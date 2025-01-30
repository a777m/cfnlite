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


def _subnet():
    """Mock Subnet yaml definition."""
    subnet = """
    resources:
      subnet:
        availabilityZone: eu-west-2b
    """
    yaml=YAML()
    block = yaml.load(subnet)
    return block


def test_subnet_build__happy():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    subnet = _subnet()

    cfnlite.subnet.build("testSubnet", callbacks, subnet["resources"]["subnet"])

    expected = {
        "Resources": {
            "testSubnet": {
                "Properties": {
                    "AvailabilityZone": "eu-west-2b",
                    "CidrBlock": "10.0.1.0/24",
                    "VpcId": "fake-vpc-id",
                },
                "Type": "AWS::EC2::Subnet",
            }
        }
    }

    assert template.to_dict() == expected


def test_subnet_build__tags():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    subnet = _subnet()

     # add tags
    tags = {"tag1": "value1", "tag2": "value2"}
    subnet["resources"]["subnet"]["tags"] = tags

    cfnlite.subnet.build("testSubnet", callbacks, subnet["resources"]["subnet"])

    expected = {
        "Resources": {
            "testSubnet": {
                "Properties": {
                    "AvailabilityZone": "eu-west-2b",
                    "CidrBlock": "10.0.1.0/24",
                    "Tags": [
                        {"Key": "default-cfnlite-resource-name", "Value": "testSubnet"},
                        {"Key": "tag1", "Value": "value1"},
                        {"Key": "tag2", "Value": "value2"},
                    ],
                    "VpcId": "fake-vpc-id",
                },
                "Type": "AWS::EC2::Subnet",
            }
        }
    }

    assert template.to_dict() == expected


def test_subnet_build__reference():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    subnet = _subnet()

    # create vpc for reference
    vpc = troposphere.ec2.VPC("testVPC", CidrBlock="10.0.0.0/16")
    # add to template and symbol table
    callbacks["add_resource"](vpc)
    callbacks["add_symbol"]("vpc", vpc)

    # add reference
    subnet["resources"]["subnet"]["vpcid"] = "ref vpc"

    cfnlite.subnet.build("testSubnet", callbacks, subnet["resources"]["subnet"])

    expected = {
        "Resources": {
            "testVPC": {
                "Properties": {
                    "CidrBlock": "10.0.0.0/16",
                },
                "Type": "AWS::EC2::VPC",
            },
            "testSubnet": {
                "Properties": {
                    "AvailabilityZone": "eu-west-2b",
                    "CidrBlock": "10.0.1.0/24",
                    "VpcId": {"Ref": "testVPC"},
                },
                "Type": "AWS::EC2::Subnet",
            }
        }
    }

    assert template.to_dict() == expected


def test_subnet_build__networkacl_connection_created():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    subnet = _subnet()

    # create networkAcl to ensure its generated
    nacl = troposphere.ec2.NetworkAcl("testNacl", VpcId="fake-vpc-id")
    # add to template and symbol table
    callbacks["add_resource"](nacl)
    callbacks["add_symbol"]("networkacl", nacl)

    cfnlite.subnet.build("testSubnet", callbacks, subnet["resources"]["subnet"])

    expected = {
        "Resources": {
            "testNacl": {
                "Properties": {
                    "VpcId": "fake-vpc-id",
                },
                "Type": "AWS::EC2::NetworkAcl",
            },
            "testSubnet": {
                "Properties": {
                    "AvailabilityZone": "eu-west-2b",
                    "CidrBlock": "10.0.1.0/24",
                    "VpcId": "fake-vpc-id",
                },
                "Type": "AWS::EC2::Subnet",
            },
            "testSubnetSubnetToNACL": {
                "Properties": {
                    "NetworkAclId": {"Ref": "testNacl"},
                    "SubnetId": {"Ref": "testSubnet"},
                },
                "Type": "AWS::EC2::SubnetNetworkAclAssociation",
            },
        }
    }

    assert template.to_dict() == expected


def test_subnet_build__routetable_connection_created():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    subnet = _subnet()

    # create networkAcl to ensure its generated
    routetable = troposphere.ec2.RouteTable("testRouteTable", VpcId="fake-vpc-id")
    # add to template and symbol table
    callbacks["add_resource"](routetable)
    callbacks["add_symbol"]("routetable", routetable)

    cfnlite.subnet.build("testSubnet", callbacks, subnet["resources"]["subnet"])

    expected = {
        "Resources": {
            "testRouteTable": {
                "Properties": {
                    "VpcId": "fake-vpc-id",
                },
                "Type": "AWS::EC2::RouteTable",
            },
            "testSubnet": {
                "Properties": {
                    "AvailabilityZone": "eu-west-2b",
                    "CidrBlock": "10.0.1.0/24",
                    "VpcId": "fake-vpc-id",
                },
                "Type": "AWS::EC2::Subnet",
            },
            "testSubnetSubnetToRouteTable": {
                "Properties": {
                    "RouteTableId": {"Ref": "testRouteTable"},
                    "SubnetId": {"Ref": "testSubnet"},
                },
                "Type": "AWS::EC2::SubnetRouteTableAssociation",
            },
        }
    }

    assert template.to_dict() == expected
