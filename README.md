## CFNLite
***
CFNLite is a 0 to 1 CloudFormation template generater built on YAML

```yaml
name: cfnLiteEc2Example
resources:
  ec2:
    dependson: ref securitygroups
    securityGroups:
      - ref securitygroups
      - default
  securitygroups:
    groupDescription: Handle inbound and outbound traffic
    securityGroupIngress: [http, ssh, icmp, https]
    securityGroupEgress: [http, ssh, icmp]
```

cnflite aims to make the process of writing CloudFormation as simple and pain
free as possible by simplifying the property semantics and offering sensible
defaults. A core tennet of cnflite is to not try produce perfect CFN but rather
generate good-enough CFN as simply and quickly as possible.

[More Examples](examples.md)

#### Why (and why not just use CDK)?
YAML is language agnostic and its declarative nature makes it relatively easy
to read. This readability is especially useful for more operation oriented
teams while trying to triage and debug in-life infrastructure issues. On the
other hand YAML is extremely fiddly, error prone and lacks any kind of real
IDE support, which more often than not leads to copy-pasta. This is compounded
by CloudFormations very limited template validation.

CDK, and other imperative IaC, fundamentally require a certain level of
programming comfort and team wide agreements on the choice of language and
process. While it makes writing CloudFormation easier, imperative approaches don't
always lend themselves to being easy to read/understand or follow
at a glance. Also, shitty code is shitty code regardless of what the output is,
its significantly more difficult to write shitty YAML.

CNFLite aims to sit in the middles of these two extremes but maintaining YAML
as the core interface but adding features and simplifications on top to make
creating CFN templates quicker, simpler and less error prone.

The main features currently offered by cfnlite:
- 'flattens' the CloudFormation yaml structure to make writing yaml easier
- Removes the need for PascalCase
- Allows naming AWS resources using their 'human' names, no need
to look up the 'Type' string
- Resource defaults make generating CloudFormation really easy
- Dynamically resolves resource dependencies

CNFLite is heavily inspired by and ~~steals~~ borrows from Ansible.

#### Installation
Clone this repository and from inside the cnflite project folder run the following:
```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m cnflite --help

#to run cfnlite on a file
venv/bin/python -m cfnlite --in-file <path-to-file> --dry-run
```
cnflite supports python 3.10+

#### Goals/road map
- ~~Generate correct CFN~~
- ~~Generate CNF with arbitrary kwargs~~
- ~~Remove the need for property PascalCase~~
- ~~Add 'ref' keyword and resolve resource dependencies~~
- ~~Add support for tagging~~
- Add loops i.e. create multiple types of the same resource with different
properties
- Add support for other CFN template sections i.e. parameters, outputs etc
- Add simple conditionals - we may be flying too close to Turing completeness
here :/
