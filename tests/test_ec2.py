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


def _ec2():
    """Mock EC2 yaml definition."""
    ec2 = """
    resources:
      ec2:
        instancetype: t2.micro
        imageid: ami-0b45ae66668865cd6
        SecurityGroups: default
    """
    yaml=YAML()
    block = yaml.load(ec2)
    return block


def test_ec2_build__happy():
    # set up
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    ec2 = _ec2()

    # test starts here
    cfnlite.ec2.build("testEC2", callbacks, ec2["resources"]["ec2"])

    expected = {
        "Resources": {
            "testEC2": {
                "Properties": {
                    "ImageId": "ami-0b45ae66668865cd6",
                    "InstanceType": "t2.micro",
                    "SecurityGroups": ["default"],
                },
                "Type": "AWS::EC2::Instance",
            }
        }
    }

    assert template.to_dict() == expected


def test_ec2_build__sgs_are_already_list():
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    ec2 = _ec2()

    # update security groups to a list
    ec2["resources"]["ec2"]["SecurityGroups"] = ["default"]

    cfnlite.ec2.build("testEC2", callbacks, ec2["resources"]["ec2"])

    expected = {
        "Resources": {
            "testEC2": {
                "Properties": {
                    "ImageId": "ami-0b45ae66668865cd6",
                    "InstanceType": "t2.micro",
                    "SecurityGroups": ["default"],
                },
                "Type": "AWS::EC2::Instance",
            }
        }
    }

    assert template.to_dict() == expected


def test_ec2_build__duplicate_props_but_difference_case():
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    ec2 = _ec2()

    # update security groups -in lowercase - to a different value
    # Although this is fine from the yaml perspective, as each key is hashed
    # to a different bucket, we dont want to accept this during building
    ec2["resources"]["ec2"]["securitygroups"] = ["notDefault"]

    with pytest.raises(ValueError):
        cfnlite.ec2.build("testEC2", callbacks, ec2["resources"]["ec2"])


def test_ec2_build__with_reference_but_not_as_list():
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    ec2 = _ec2()

    # create security group reference
    sg = troposphere.ec2.SecurityGroup(
        "TestSecurityGroupsName", GroupDescription="aFakeGroupID")

    # add to template and symbol table
    callbacks["add_resource"](sg)
    callbacks["add_symbol"]("securitygroups", sg)

    # update security groups reference
    ec2["resources"]["ec2"]["SecurityGroups"] = "ref securitygroups"

    cfnlite.ec2.build("testEC2", callbacks, ec2["resources"]["ec2"])

    expected = {
        "Resources": {
            "TestSecurityGroupsName": {
                "Properties": {
                    "GroupDescription": "aFakeGroupID",
                },
                "Type": "AWS::EC2::SecurityGroup",
            },
            "testEC2": {
                "Properties": {
                    "ImageId": "ami-0b45ae66668865cd6",
                    "InstanceType": "t2.micro",
                    "SecurityGroups": [{"Ref": "TestSecurityGroupsName"}],
                },
                "Type": "AWS::EC2::Instance",
            }
        }
    }

    assert template.to_dict() == expected


def test_ec2_build__with_reference_as_list():
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    ec2 = _ec2()

    # create security group reference
    sg = troposphere.ec2.SecurityGroup(
        "TestSecurityGroupsName", GroupDescription="aFakeGroupID")

    # add to template and symbol table
    callbacks["add_resource"](sg)
    callbacks["add_symbol"]("securitygroups", sg)

    # update security groups reference
    ec2["resources"]["ec2"]["SecurityGroups"] = ["ref securitygroups"]

    cfnlite.ec2.build("testEC2", callbacks, ec2["resources"]["ec2"])

    expected = {
        "Resources": {
            "TestSecurityGroupsName": {
                "Properties": {
                    "GroupDescription": "aFakeGroupID",
                },
                "Type": "AWS::EC2::SecurityGroup",
            },
            "testEC2": {
                "Properties": {
                    "ImageId": "ami-0b45ae66668865cd6",
                    "InstanceType": "t2.micro",
                    "SecurityGroups": [{"Ref": "TestSecurityGroupsName"}],
                },
                "Type": "AWS::EC2::Instance",
            }
        }
    }

    assert template.to_dict() == expected


# we want to test ref keywords with nothing after and with lots of stuff
# after them
@pytest.mark.parametrize("bad_ref", ["ref", "ref abc def", "ref abc def hij"])
def test_ec2_build__bad_ref(bad_ref):
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    ec2 = _ec2()

    # add ref keyword with nothing following
    ec2["resources"]["ec2"]["SecurityGroups"] = bad_ref

    with pytest.raises(ValueError):
        cfnlite.ec2.build("testEC2", callbacks, ec2["resources"]["ec2"])


@pytest.mark.parametrize("bad_ref", ["ref", "ref abc def", "ref abc def hij"])
def test_ec2_build__bad_ref_with_as_list(bad_ref):
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    ec2 = _ec2()

    # add ref keyword with nothing following
    ec2["resources"]["ec2"]["SecurityGroups"] = [bad_ref]

    with pytest.raises(ValueError):
        cfnlite.ec2.build("testEC2", callbacks, ec2["resources"]["ec2"])


def test_ec2_build__bad_ref_does_not_exist():
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    ec2 = _ec2()

    # add ref keyword with nothing following
    ec2["resources"]["ec2"]["SecurityGroups"] = ["ref fake-ref"]

    with pytest.raises(KeyError):
        cfnlite.ec2.build("testEC2", callbacks, ec2["resources"]["ec2"])


def test_ec2_build__from_raw_e2e_with_ref():
    # raw ec2 definition to test agaist e2e
    ec2_tmp = """
    resources:
      ec2:
        instancetype: t2.micro
        imageid: ami-0b45ae66668865cd6
        SecurityGroups:
          - default
          - ref securitygroups
    """
    yaml=YAML()
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    ec2 = yaml.load(ec2_tmp)

    # create security group reference
    sg = troposphere.ec2.SecurityGroup(
        "TestSecurityGroupsName",
        GroupDescription="aFakeGroupID",
        SecurityGroupIngress=[],
    )

    # add to template and symbol table
    callbacks["add_resource"](sg)
    callbacks["add_symbol"]("securitygroups", sg)

    cfnlite.ec2.build("testEC2", callbacks, ec2["resources"]["ec2"])

    expected = {
        "Resources": {
            "TestSecurityGroupsName": {
                "Properties": {
                    "GroupDescription": "aFakeGroupID",
                    "SecurityGroupIngress": [],
                },
                "Type": "AWS::EC2::SecurityGroup",
            },
            "testEC2": {
                "Properties": {
                    "ImageId": "ami-0b45ae66668865cd6",
                    "InstanceType": "t2.micro",
                    "SecurityGroups": [
                        "default",
                        {"Ref": "TestSecurityGroupsName"},
                    ],
                },
                "Type": "AWS::EC2::Instance",
            }
        }
    }

    assert template.to_dict() == expected


@pytest.mark.parametrize("key,value", [
    ("AdditionalInfo", "test-additional-info"),
    ("Affinity", "host"),
    ("AvailabilityZone", "eu-zone-1"),
    ("PrivateIpAddress", "127.0.0.1"),
    ("SubnetId", "some-subnet-id"),
])
def test_ec2_build__pass_possible_values(key, value):
    template = troposphere.Template()
    callbacks = mock_callbacks(template)
    ec2 = _ec2()

    # add value in lower case to ensure its proper parsed
    ec2["resources"]["ec2"][key.lower()] = value
    # add a resource attribute value
    ec2["resources"]["ec2"]["dependson"] = "test-depends-on"

    # test starts here
    cfnlite.ec2.build("testEC2", callbacks, ec2["resources"]["ec2"])

    expected = {
        "Resources": {
            "testEC2": {
                "DependsOn": "test-depends-on",
                "Properties": {
                    "ImageId": "ami-0b45ae66668865cd6",
                    "InstanceType": "t2.micro",
                    "SecurityGroups": ["default"],
                    key: value,
                },
                "Type": "AWS::EC2::Instance",
            }
        }
    }

    assert template.to_dict() == expected
