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


def _routetable():
    """Mock routetable yaml definition."""
    routetable = """
    resources:
      routetable:
        vpcId: example-vpc-id
    """
    yaml=YAML()
    block = yaml.load(routetable)
    return block


def test_routetable_build__happy():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    routetable = _routetable()

    cfnlite.route_table.build("testRouteTable", callbacks, routetable["resources"]["routetable"])

    expected = {
        "Resources": {
            "testRouteTable": {
                "Properties": {
                    "VpcId": "example-vpc-id",
                },
                "Type": "AWS::EC2::RouteTable",
            }
        }
    }

    assert template.to_dict() == expected


def test_routetable_build__tags():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    routetable = _routetable()

     # add tags
    tags = {"tag1": "value1", "tag2": "value2"}
    routetable["resources"]["routetable"]["tags"] = tags

    cfnlite.route_table.build("testRouteTable", callbacks, routetable["resources"]["routetable"])

    expected = {
        "Resources": {
            "testRouteTable": {
                "Properties": {
                    "Tags": [
                        {"Key": "default-cfnlite-resource-name", "Value": "testRouteTable"},
                        {"Key": "tag1", "Value": "value1"},
                        {"Key": "tag2", "Value": "value2"},
                    ],
                    "VpcId": "example-vpc-id",
                },
                "Type": "AWS::EC2::RouteTable",
            }
        }
    }

    assert template.to_dict() == expected


def test_routetable_build__reference():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    routetable = _routetable()

    # create vpc for reference
    vpc = troposphere.ec2.VPC("testVPC", CidrBlock="10.0.0.0/16")
    # add to template and symbol table
    callbacks["add_resource"](vpc)
    callbacks["add_symbol"]("vpc", vpc)

    # add reference
    routetable["resources"]["routetable"]["vpcId"] = "ref! vpc"

    cfnlite.route_table.build("testRouteTable", callbacks, routetable["resources"]["routetable"])

    expected = {
        "Resources": {
            "testVPC": {
                "Properties": {
                    "CidrBlock": "10.0.0.0/16",
                },
                "Type": "AWS::EC2::VPC",
            },
            "testRouteTable": {
                "Properties": {
                    "VpcId": {"Ref": "testVPC"},
                },
                "Type": "AWS::EC2::RouteTable",
            }
        }
    }

    assert template.to_dict() == expected


def test_routetable_build__igw_connection_created():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    routetable = _routetable()

    # create igw to ensure its generated
    igw = troposphere.ec2.InternetGateway("testIGW")
    # add to template and symbol table
    callbacks["add_resource"](igw)
    callbacks["add_symbol"]("internetgateway", igw)

    cfnlite.route_table.build("testRouteTable", callbacks, routetable["resources"]["routetable"])

    expected = {
        "Resources": {
            "testIGW": {
                "Type": "AWS::EC2::InternetGateway"
            },
            "testRouteTable": {
                "Properties": {
                    "VpcId": "example-vpc-id",
                },
                "Type": "AWS::EC2::RouteTable",
            },
            "testRouteTableRouteToIGW": {
                "Properties": {
                    "DestinationCidrBlock": "0.0.0.0/0",
                    "GatewayId": {"Ref": "testIGW"},
                    "RouteTableId": {"Ref": "testRouteTable"},
                },
                "Type": "AWS::EC2::Route",
            },
        }
    }

    assert template.to_dict() == expected
