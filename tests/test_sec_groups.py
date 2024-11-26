"""Tests for security groups."""

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


def _sg():
    """Simple mock security groups definition."""
    sg = """
    resources:
      securitygroups:
        groupdescription: Handle inbound and outbound traffic
        securitygroupingress: [http]
        securitygroupegress: [http]
    """
    yaml=YAML()
    block = yaml.load(sg)
    return block


def test_sg_build__happy():
    # setup
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    sg = _sg()

    # test starts here
    cfnlite.securitygroups.build(
        "testSGs", callbacks, sg["resources"]["securitygroups"])

    expected = {
        "testSGs": {
            "Properties": {
                "GroupDescription": "Handle inbound and outbound traffic",
                "SecurityGroupEgress": [{
                    "Properties": {
                        "CidrIp": "0.0.0.0/0",
                        "GroupId": {
                            "Fn::GetAtt": ["testSGs", "GroupId"],
                        },
                        "Description": "Outbound HTTP traffic",
                        "IpProtocol": "tcp",
                        "FromPort": 80,
                        "ToPort": 80,
                    },
                    "Type": "AWS::EC2::SecurityGroupEgress",
                }],
                "SecurityGroupIngress": [{
                    "Properties": {
                        "CidrIp": "0.0.0.0/0",
                        "GroupId": {
                            "Fn::GetAtt": ["testSGs", "GroupId"],
                        },
                        "Description": "Inbound HTTP traffic",
                        "IpProtocol": "tcp",
                        "FromPort": 80,
                        "ToPort": 80,
                    },
                    "Type": "AWS::EC2::SecurityGroupIngress",
                }],
            },
            "Type": "AWS::EC2::SecurityGroup",
        },
    }

    assert template.to_dict()["Resources"] == expected


def test_sg_build__ensure_icmp_is_correct():
    # setup
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    sg = _sg()

    # add icmp to sg rules
    sg["resources"]["securitygroups"]["securitygroupingress"] = ["icmp"]
    sg["resources"]["securitygroups"]["securitygroupegress"] = ["icmp"]

    # test starts here
    cfnlite.securitygroups.build(
        "testSGs", callbacks, sg["resources"]["securitygroups"])

    expected = {
        "testSGs": {
            "Properties": {
                "GroupDescription": "Handle inbound and outbound traffic",
                "SecurityGroupEgress": [{
                    "Properties": {
                        "CidrIp": "0.0.0.0/0",
                        "GroupId": {
                            "Fn::GetAtt": ["testSGs", "GroupId"],
                        },
                        "Description": "Outbound ICMP traffic",
                        "IpProtocol": "icmp",
                        "FromPort": 0,
                        "ToPort": 0,
                    },
                    "Type": "AWS::EC2::SecurityGroupEgress",
                }],
                "SecurityGroupIngress": [{
                    "Properties": {
                        "CidrIp": "0.0.0.0/0",
                        "GroupId": {
                            "Fn::GetAtt": ["testSGs", "GroupId"],
                        },
                        "Description": "Inbound ICMP traffic",
                        "IpProtocol": "icmp",
                        "FromPort": 8,
                        "ToPort": 0,
                    },
                    "Type": "AWS::EC2::SecurityGroupIngress",
                }],
            },
            "Type": "AWS::EC2::SecurityGroup",
        },
    }

    assert template.to_dict()["Resources"] == expected

def test_sg_build__no_ingress_or_egress():
    # setup
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    sg = _sg()

    # update security groups to empty lists
    sg["resources"]["securitygroups"]["securitygroupingress"] = []
    sg["resources"]["securitygroups"]["securitygroupegress"] = []

    cfnlite.securitygroups.build(
        "testSGs", callbacks, sg["resources"]["securitygroups"])

    expected = {
        "testSGs": {
            "Properties": {
                "GroupDescription": "Handle inbound and outbound traffic",
                "SecurityGroupEgress": [],
                "SecurityGroupIngress": [],
            },
            "Type": "AWS::EC2::SecurityGroup",
        },
    }

    assert template.to_dict()["Resources"] == expected


def test_sg_build__pass_sg_rule_as_string():
    # setup
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    sg = _sg()

    # update ingress to empty list
    sg["resources"]["securitygroups"]["securitygroupingress"] = []
    # pass http rule as a string
    sg["resources"]["securitygroups"]["securitygroupegress"] = "http"

    cfnlite.securitygroups.build(
        "testSGs", callbacks, sg["resources"]["securitygroups"])

    expected = {
        "testSGs": {
            "Properties": {
                "GroupDescription": "Handle inbound and outbound traffic",
                "SecurityGroupEgress": [{
                    "Properties": {
                        "CidrIp": "0.0.0.0/0",
                        "GroupId": {
                            "Fn::GetAtt": ["testSGs", "GroupId"],
                        },
                        "Description": "Outbound HTTP traffic",
                        "IpProtocol": "tcp",
                        "FromPort": 80,
                        "ToPort": 80,
                    },
                    "Type": "AWS::EC2::SecurityGroupEgress",
                }],
                "SecurityGroupIngress": [],
            },
            "Type": "AWS::EC2::SecurityGroup",
        },
    }

    assert template.to_dict()["Resources"] == expected


# test unknown protocol
# While this may seem like a bad idea, we don't want to limit people to having
# to define rules only using the pre-defined protocols. This allows users to
# generate most of the ingress/egress rule and only requires them to change
# the FromPort and ToPort in the generated CNF.
def test_sg_build__check_unknown_proto_generates_http():
    # setup
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    sg = _sg()

    # add unknown to sg rules
    sg["resources"]["securitygroups"]["securitygroupegress"] = ["fakeProtocol"]
    sg["resources"]["securitygroups"]["securitygroupingress"] = []

    # test starts here
    cfnlite.securitygroups.build(
        "testSGs", callbacks, sg["resources"]["securitygroups"])

    expected = {
        "testSGs": {
            "Properties": {
                "GroupDescription": "Handle inbound and outbound traffic",
                "SecurityGroupEgress": [{
                    "Properties": {
                        "CidrIp": "0.0.0.0/0",
                        "GroupId": {
                            "Fn::GetAtt": ["testSGs", "GroupId"],
                        },
                        "Description": "Outbound FAKEPROTOCOL traffic",
                        "IpProtocol": "tcp",
                        "FromPort": 80,
                        "ToPort": 80,
                    },
                    "Type": "AWS::EC2::SecurityGroupEgress",
                }],
                "SecurityGroupIngress": [],
            },
            "Type": "AWS::EC2::SecurityGroup",
        },
    }

    assert template.to_dict()["Resources"] == expected


def test_sg_build__pass_all_possible_properties():
    # setup
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    sg = _sg()

    # reset security group rules
    sg["resources"]["securitygroups"]["securitygroupingress"] = []
    sg["resources"]["securitygroups"]["securitygroupegress"] = []

    sg["resources"]["securitygroups"]["groupName"] = "This-is-a-gp-name"
    sg["resources"]["securitygroups"]["vpcId"] = "id-vpc1234"

    # add a resource attribute value
    sg["resources"]["securitygroups"]["dependson"] = "test-depends-on"

    cfnlite.securitygroups.build(
        "testSGs", callbacks, sg["resources"]["securitygroups"])

    expected = {
        "testSGs": {
            "DependsOn": "test-depends-on",
            "Properties": {
                "GroupDescription": "Handle inbound and outbound traffic",
                "GroupName": "This-is-a-gp-name",
                "SecurityGroupEgress": [],
                "SecurityGroupIngress": [],
                "VpcId": "id-vpc1234",
            },
            "Type": "AWS::EC2::SecurityGroup",
        },
    }

    assert template.to_dict()["Resources"] == expected


def test_sg_build__double_named_property():
    # setup
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    sg = _sg()

    # add security group ingress but in different case
    sg["resources"]["securitygroups"]["securitygroupIngress"] = []

    with pytest.raises(ValueError) as e:
        cfnlite.securitygroups.build(
            "testSGs", callbacks, sg["resources"]["securitygroups"])

    assert str(e.value) == (
        "Each property can only be used once. "
        "Offending prop: securitygroupIngress")


@pytest.mark.parametrize("bad_prop",
    ["iAmFake", "fake-with-dash", "fake with space"]
)
def test_sg_build__invalid_proptery_name(bad_prop):
    # setup
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    sg = _sg()

    # add fake property to SG
    sg["resources"]["securitygroups"][bad_prop] = "FakeValue"

    with pytest.raises(ValueError) as e:
        cfnlite.securitygroups.build(
            "testSGs", callbacks, sg["resources"]["securitygroups"])

    assert str(e.value) == \
        f"{bad_prop} is not a valid attribute for SecurityGroups"


@pytest.mark.xfail(
    reason="There is no real way around this issue, this will raise an "
           "attribute error in troposphere. We could validate on our side but "
           "that will be a future change.")
def test_sg_build__pass_prop_in_lang_but_invalid_property():
    # setup
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    sg = _sg()

    # reset security group rules
    sg["resources"]["securitygroups"]["ingress"] = []

    cfnlite.securitygroups.build(
        "testSGs", callbacks, sg["resources"]["securitygroups"])
