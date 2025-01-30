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


def _nacl():
    """Mock NACL yaml definition."""
    nacl = """
    resources:
      networkAcl:
        ingress: [http]
        egress: [http]
    """
    yaml=YAML()
    block = yaml.load(nacl)
    return block


def test_nacl_build__happy():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    nacl = _nacl()

    cfnlite.networkacl.build("testNACL", callbacks, nacl["resources"]["networkAcl"])

    expected = {
        "Resources": {
            "testNACL": {
                "Properties": {
                    "VpcId": "id-example-vpc",
                },
                "Type": "AWS::EC2::NetworkAcl"
            },
            "testNACLRuleHTTPIn": {
                "Properties": {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": False,
                    "NetworkAclId": {"Ref": "testNACL"},
                    "PortRange": {
                        "From": 80,
                        "To": 80,
                    },
                    "Protocol": 6,
                    "RuleAction": "allow",
                    "RuleNumber": 80,
                },
                "Type": "AWS::EC2::NetworkAclEntry",
            },
            "testNACLRuleHTTPOut": {
                "Properties": {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": True,
                    "NetworkAclId": {"Ref": "testNACL"},
                    "PortRange": {
                        "From": 80,
                        "To": 80,
                    },
                    "Protocol": 6,
                    "RuleAction": "allow",
                    "RuleNumber": 80,
                },
                "Type": "AWS::EC2::NetworkAclEntry",
            },
        },
    }

    assert template.to_dict() == expected


def test_nacl_build__icmp():
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    nacl = _nacl()

    # make ingress and egress icmp
    nacl["resources"]["networkAcl"]["egress"] = ["icmp"]
    nacl["resources"]["networkAcl"]["ingress"] = ["icmp"]

    cfnlite.networkacl.build("testNACL", callbacks, nacl["resources"]["networkAcl"])

    expected = {
        "Resources": {
            "testNACL": {
                "Properties": {
                    "VpcId": "id-example-vpc",
                },
                "Type": "AWS::EC2::NetworkAcl"
            },
            "testNACLRuleICMPIn": {
                "Properties": {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": False,
                    "NetworkAclId": {"Ref": "testNACL"},
                    "Icmp": {
                        "Code": 0,
                        "Type": 8,
                    },
                    "Protocol": 1,
                    "RuleAction": "allow",
                    "RuleNumber": 100,
                },
                "Type": "AWS::EC2::NetworkAclEntry",
            },
            "testNACLRuleICMPOut": {
                "Properties": {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": True,
                    "NetworkAclId": {"Ref": "testNACL"},
                    "Icmp": {
                        "Code": 0,
                        "Type": 0,
                    },
                    "Protocol": 1,
                    "RuleAction": "allow",
                    "RuleNumber": 100,
                },
                "Type": "AWS::EC2::NetworkAclEntry",
            },
        },
    }

    assert template.to_dict() == expected


def test_nacl_build__rule_input_is_string():
    """Ensure a single param can be passed as a string a not list."""
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    nacl = _nacl()

    # make ingress a string
    nacl["resources"]["networkAcl"]["egress"] = []
    nacl["resources"]["networkAcl"]["ingress"] = "http"

    cfnlite.networkacl.build("testNACL", callbacks, nacl["resources"]["networkAcl"])

    expected = {
        "Resources": {
            "testNACL": {
                "Properties": {
                    "VpcId": "id-example-vpc",
                },
                "Type": "AWS::EC2::NetworkAcl"
            },
            "testNACLRuleHTTPIn": {
                "Properties": {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": False,
                    "NetworkAclId": {"Ref": "testNACL"},
                    "PortRange": {
                        "From": 80,
                        "To": 80,
                    },
                    "Protocol": 6,
                    "RuleAction": "allow",
                    "RuleNumber": 80,
                },
                "Type": "AWS::EC2::NetworkAclEntry",
            },
        },
    }

    assert template.to_dict() == expected


def test_nacl_build__rule_input_string_with_spaces():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    nacl = _nacl()

    # make ingress a string
    nacl["resources"]["networkAcl"]["egress"] = []
    nacl["resources"]["networkAcl"]["ingress"] = "http https"

    # this error is raise by troposphere, we should probably do our own
    # alphanumeric error checking for inputs
    with pytest.raises(ValueError) as err:
        cfnlite.networkacl.build(
            "testNACL", callbacks, nacl["resources"]["networkAcl"])

    assert str(err.value) == 'Name "testNACLRuleHTTP HTTPSIn" not alphanumeric'


def test_nacl_build__unknown_protocol_generates_http():
     # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    nacl = _nacl()

    # make ingress a string
    nacl["resources"]["networkAcl"]["egress"] = []
    nacl["resources"]["networkAcl"]["ingress"] = "unknown"

    cfnlite.networkacl.build("testNACL", callbacks, nacl["resources"]["networkAcl"])

    expected = {
        "Resources": {
            "testNACL": {
                "Properties": {
                    "VpcId": "id-example-vpc",
                },
                "Type": "AWS::EC2::NetworkAcl"
            },
            "testNACLRuleUNKNOWNIn": {
                "Properties": {
                    "CidrBlock": "0.0.0.0/0",
                    "Egress": False,
                    "NetworkAclId": {"Ref": "testNACL"},
                    "PortRange": {
                        "From": 80,
                        "To": 80,
                    },
                    "Protocol": 6,
                    "RuleAction": "allow",
                    "RuleNumber": 80,
                },
                "Type": "AWS::EC2::NetworkAclEntry",
            },
        },
    }

    assert template.to_dict() == expected
