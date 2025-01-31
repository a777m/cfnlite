## Examples
Generally speaking, valid YAML is valid CFNLite. For a full list of properties supported on each resources
run `cfnlite --explain <resource-name>`

# Table of contents
1. [EC2](#ec2)
2. [Security Groups](#sgs)
3. [IAM](#iam)
    1. [To inline policy or to not](#inlinepol)
4. [Refs](#references)
    1. [Resource attributes](#resourceattr)
5. [Networking deep dive](#net)
    1. [VPC](#vpc)
    2. [Network access control lists](#nacl)
    3. [cfnlite gets smart](#cfnsmart)
    4. [Full network example](#fullnet)

<a name="ec2"></a>
#### EC2
```yaml
name: cfnLiteEC2SuperSimpleExample
resources:
  ec2:
    tags:
      name: bastion-host
```
The above example generates the following
```yaml
Resources:
  cfnLiteEC2SuperSimpleExampleEC2:
    Properties:
      ImageId: ami-0b45ae66668865cd6
      InstanceType: t2.micro
      SecurityGroups:
        - default
      Tags:
        - Key: default-cfnlite-resource-name
          Value: cfnLiteEC2SuperSimpleExampleEC2
        - Key: name
          Value: bastion-host
    Type: AWS::EC2::Instance
```
Of the cnflite supported AWS resources, this is probably the simplest example.
Each resource comes with defaults for all the required fields so you don't need
pass more property values than needed.

Some things to note:
- for each resource you do need to pass at least on property, the simples of
which is probably a single tag - tags are available for all top level
resources supported by cfnlite.
- cfnlite requires a name field, this is used as part of giving resources
unique names
- you can overwrite any of the supported properties
- if the property expects a list, you can pass single values as a string.
In the case above 'default' would be fine as a string.
- property names need not be PascalCase, they can be formatted however you see
fit (all still one word)
- Property names must match those of CloudFormation

<a name="sgs"></a>
#### Security Groups
```yaml
name: cfnLiteSGExample
resources:
  securitygroups:
    GroupDescription: Handle inbound and outbound traffic
    securitygroupIngress: [http]
    securitygroupEgress: [http]
```
The above generates the following:
```yaml
Resources:
  cfnLiteSGExampleSECURITYGROUPS:
    Properties:
      GroupDescription: Handle inbound and outbound traffic
      SecurityGroupEgress:
        - Properties:
            CidrIp: '0.0.0.0/0'
            Description: Outbound HTTP traffic
            FromPort: 80
            GroupId: !GetAtt 'cfnLiteSGExampleSECURITYGROUPS.GroupId'
            IpProtocol: tcp
            ToPort: 80
          Type: AWS::EC2::SecurityGroupEgress
      SecurityGroupIngress:
        - Properties:
            CidrIp: '0.0.0.0/0'
            Description: Inbound HTTP traffic
            FromPort: 80
            GroupId: !GetAtt 'cfnLiteSGExampleSECURITYGROUPS.GroupId'
            IpProtocol: tcp
            ToPort: 80
          Type: AWS::EC2::SecurityGroupIngress
    Type: AWS::EC2::SecurityGroup
```
Security groups are defined very similarly to EC2s and all the points above
apply to them too.
Some security group specifics:
- Security group ingress/egress take a list of the protocol names
the protocol specific details are handled for you
- The options are predefined, the available options are:
  - http, https, icmp, ssh, psql, mysql, redis, memcached, smtp (25), ntp and
  mongo
- For a custom port, pass in the name of your "protocol" and it will generate a
standard http ingress/egress, from there you can easily change the port numbers
to match yours
- Currently, you can only change the top level SecurityGroups properties i.e.
you cannot change ingress/egress properties. This will be fixed in a future
version

<a name="iam"></a>
#### IAM
```yaml
name: cfnLiteRoleExample
resources:
  role:
    AssumeRolePolicyDocument:
      Principal:
        service: "ec2.amazonaws.com"
      Action:
        - "sts:AssumeRole"
```
Above generates the following
```yaml
Resources:
  cfnLiteRoleExampleROLE:
    Properties:
      AssumeRolePolicyDocument:
        PolicyDocument:
          Statement:
            - Action:
                - sts:AssumeRole
              Effect: Allow
              Principal:
                service: ec2.amazonaws.com
              Resources:
                - '*'
          Version: '2012-10-17'
      RoleName: TestRole
    Type: AWS::IAM::Role
```
Annoyingly, IAM, mainly due to policy documents, is one of the most nested CloudFormation template types.
cfnlite tries to strike a balance between flattening the structure, to make writing policy documents easier, and
maintaining the clear relationships between properties.
Some policy document specifics:
- Policy documents come with the standard defaults out of the box i.e.
Action: Allow and Resources: *
- You can overwrite any value in the policy document e.g. Effect: Deny
- You can pass in an arbitrary amount of actions for a document
- cnflite knows the special cases of documents that have the Principal field

<a name="inlinepol"></a>
##### To inline policy or to not
When it comes to IAM policies cfnlite, like CNF, gives you two choices, inline
policies or a separate policy resource which you can then reference.
This first example is of inlined policies:
```yaml
name: cfnLiteRoleExample
resources:
  role:
    AssumeRolePolicyDocument:
      Principal:
        service: "ec2.amazonaws.com"
      Action:
        - "sts:AssumeRole"
    policies:
      - Action: "cloudwatch:*"
      - Action: "lakeformation:*"
```
generates
```yaml
Resources:
  cfnLiteRoleExampleROLE:
    Properties:
      AssumeRolePolicyDocument:
        PolicyDocument:
          Statement:
            - Action:
                - sts:AssumeRole
              Effect: Allow
              Principal:
                service: ec2.amazonaws.com
              Resources:
                - '*'
          Version: '2012-10-17'
      Policies:
        - PolicyDocument:
            Statement:
              - Action:
                  - cloudwatch:*
                Effect: Allow
                Resources:
                  - '*'
              - Action:
                  - lakeformation:*
                Effect: Allow
                Resources:
                  - '*'
            Version: '2012-10-17'
          PolicyName: Example cfnlite policy
      RoleName: TestRole
    Type: AWS::IAM::Role
```
Some notes about inlined policies:
- once you use the keyword 'policies', you can go straight into defining
your statements
- each item in the list under policies is a separate statement
- You dont have to start with Action, you can use whatever statement property
you like
- you can mix and match staments i.e. some statements can just be simple defaults
whereas others you overwrite all of the other fields.


This is an example of the other option, to have a separate policy resource
```yaml
name: cfnLitePolicyExample
resources:
  policy:
    policyName: "This is a test policy from outside"
    Statement:
      - Action: "cloudwatch:*"
      - Action: "lakeformation:*"
      - Action: "sns:*"
      - Effect: "Deny"
        Action:
          - "states:*"
        Resources: "dynamodb:*"
```
Generates
```yaml
Resources:
  cfnLitePolicyExamplePOLICY:
    Properties:
      PolicyDocument:
        Statement:
          - Action:
              - cloudwatch:*
            Effect: Allow
            Resources:
              - '*'
          - Action:
              - lakeformation:*
            Effect: Allow
            Resources:
              - '*'
          - Action:
              - sns:*
            Effect: Allow
            Resources:
              - '*'
          - Action:
              - states:*
            Effect: Deny
            Resources:
              - dynamodb:*
        Version: '2012-10-17'
      PolicyName: This is a test policy from outside
    Type: AWS::IAM::Policy
```
This example makes the relationship between statements and the list from the
inline example more explicit. In the inline example we just skipped having to
write the 'statement' keyword. Here we also see an example of over writing
some of the statement defaults.

<a name="refs"></a>
#### References
Like CFN, cfnlite allows you to reference resource which cfnlite will then resolve once the
resource has been created. In the generated CFN references are resolved to the name
of the resource created by cfnlite. Note: you directly reference a resource usings is
AWS "human" name, this is to abstract away from worrying about what resource name
is created by cfnlite.
```yaml
name: cfnLiteRefExample
resources:
  ec2:
    instanceType: t2.micro
    securityGroups: ref securitygroups
  securitygroups:
    GroupDescription: Handle inbound and outbound traffic
    securitygroupIngress: [http]
    securitygroupEgress: [http]
```
Generates
```yaml
Resources:
  cfnLiteRefExampleEC2:
    Properties:
      ImageId: ami-0b45ae66668865cd6
      InstanceType: t2.micro
      SecurityGroups:
        - !Ref 'cfnLiteRefExampleSECURITYGROUPS'
    Type: AWS::EC2::Instance
  cfnLiteRefExampleSECURITYGROUPS:
    Properties:
      GroupDescription: Handle inbound and outbound traffic
      SecurityGroupEgress:
        - Properties:
            CidrIp: '0.0.0.0/0'
            Description: Outbound HTTP traffic
            FromPort: 80
            GroupId: !GetAtt 'cfnLiteRefExampleSECURITYGROUPS.GroupId'
            IpProtocol: tcp
            ToPort: 80
          Type: AWS::EC2::SecurityGroupEgress
      SecurityGroupIngress:
        - Properties:
            CidrIp: '0.0.0.0/0'
            Description: Inbound HTTP traffic
            FromPort: 80
            GroupId: !GetAtt 'cfnLiteRefExampleSECURITYGROUPS.GroupId'
            IpProtocol: tcp
            ToPort: 80
          Type: AWS::EC2::SecurityGroupIngress
    Type: AWS::EC2::SecurityGroup
```
As this example shows more clearly, the reference is resolved using the generated
name.
Note: The syntax for references will probably change to match the syntax of CFN.

<a name="resourceattr"></a>
##### Resource attributes
cfnlite also allows you to use all the standard AWS resource attributes. So the
above could also include `DependsOn`
```yaml
name: cfnLiteDepsOnExample
resources:
  ec2:
    dependsOn: ref securitygroups
    instanceType: t2.micro
    securityGroups: ref securitygroups
  securitygroups:
    GroupDescription: Handle inbound and outbound traffic
    securitygroupIngress: [http]
    securitygroupEgress: [http]
```
Generates the following
```yaml
Resources:
  cfnLiteDepsOnExampleEC2:
    DependsOn: !Ref 'cfnLiteDepsOnExampleSECURITYGROUPS'
    Properties:
      ImageId: ami-0b45ae66668865cd6
      InstanceType: t2.micro
      SecurityGroups:
        - !Ref 'cfnLiteDepsOnExampleSECURITYGROUPS'
    Type: AWS::EC2::Instance
  cfnLiteDepsOnExampleSECURITYGROUPS:
    Properties:
      GroupDescription: Handle inbound and outbound traffic
      SecurityGroupEgress:
        - Properties:
            CidrIp: '0.0.0.0/0'
            Description: Outbound HTTP traffic
            FromPort: 80
            GroupId: !GetAtt 'cfnLiteDepsOnExampleSECURITYGROUPS.GroupId'
            IpProtocol: tcp
            ToPort: 80
          Type: AWS::EC2::SecurityGroupEgress
      SecurityGroupIngress:
        - Properties:
            CidrIp: '0.0.0.0/0'
            Description: Inbound HTTP traffic
            FromPort: 80
            GroupId: !GetAtt 'cfnLiteDepsOnExampleSECURITYGROUPS.GroupId'
            IpProtocol: tcp
            ToPort: 80
          Type: AWS::EC2::SecurityGroupIngress
    Type: AWS::EC2::SecurityGroup
```
<a name="net"></a>
#### Networking deep dive
cfnlite supports the core - and simplest subset of the CFN network stack.
Along with the security groups mentioned earlier, the following resources are
supported:
- VPC
- internet gateway
- network access control lists
- route tables
- subnets

<a name="vpc"></a>
##### VPC

```yaml
name: cfnLiteVPCSimpleExample
resources:
  vpc:
    tags:
      name: micro-service-vpc
```
Generates the following:
```yaml
Resources:
  cfnLiteVPCSimpleExampleVPC:
    Properties:
      CidrBlock: 10.0.0.0/16
      Tags:
        - Key: default-cfnlite-resource-name
          Value: cfnLiteVPCSimpleExampleVPC
        - Key: name
          Value: micro-service-vpc
    Type: AWS::EC2::VPC
```
Like many of the other cfnlite resources, you are free to define as many
or as little resources properties as you like. As long as you pass a Tag
cnflite will generally be able to figure out the rest.

<a name="nacl"></a>
##### Network access control lists
```yaml
name: cfnLiteNaclSimpleExample
resources:
  networkAcl:
    ingress: [https, redis, psql, icmp]
    egress: https
    tags:
      name: microservice NACL
```
generates the following
```yaml
Resources:
  cfnLiteNaclSimpleExampleNETWORKACL:
    Properties:
      Tags:
        - Key: default-cfnlite-resource-name
          Value: cfnLiteNaclSimpleExampleNETWORKACL
        - Key: name
          Value: microservice NACL
      VpcId: id-example-vpc
    Type: AWS::EC2::NetworkAcl
  cfnLiteNaclSimpleExampleNETWORKACLRuleHTTPSIn:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: false
      NetworkAclId: !Ref 'cfnLiteNaclSimpleExampleNETWORKACL'
      PortRange:
        From: 443
        To: 443
      Protocol: 6
      RuleAction: allow
      RuleNumber: 443
    Type: AWS::EC2::NetworkAclEntry
  cfnLiteNaclSimpleExampleNETWORKACLRuleHTTPSOut:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: true
      NetworkAclId: !Ref 'cfnLiteNaclSimpleExampleNETWORKACL'
      PortRange:
        From: 443
        To: 443
      Protocol: 6
      RuleAction: allow
      RuleNumber: 443
    Type: AWS::EC2::NetworkAclEntry
  cfnLiteNaclSimpleExampleNETWORKACLRuleICMPIn:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: false
      Icmp:
        Code: 0
        Type: 8
      NetworkAclId: !Ref 'cfnLiteNaclSimpleExampleNETWORKACL'
      Protocol: 1
      RuleAction: allow
      RuleNumber: 100
    Type: AWS::EC2::NetworkAclEntry
  cfnLiteNaclSimpleExampleNETWORKACLRulePSQLIn:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: false
      NetworkAclId: !Ref 'cfnLiteNaclSimpleExampleNETWORKACL'
      PortRange:
        From: 5432
        To: 5432
      Protocol: 6
      RuleAction: allow
      RuleNumber: 5432
    Type: AWS::EC2::NetworkAclEntry
  cfnLiteNaclSimpleExampleNETWORKACLRuleREDISIn:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: false
      NetworkAclId: !Ref 'cfnLiteNaclSimpleExampleNETWORKACL'
      PortRange:
        From: 6379
        To: 6379
      Protocol: 6
      RuleAction: allow
      RuleNumber: 6379
    Type: AWS::EC2::NetworkAclEntry
```
NACL's have the first instance of a custom cfnlite variables. In order to
make NACL rules as simple as possible (and to match SG definitions),
cfnlite introduces the `ingress` and `egress` keywords for NACLs. Passing a
list of NACL protocol rules generates the appropriate ingress and egress entries
for the NACL.

Its important to remember that `ingress` and `egress` are _not_ part of the CFN
resource definition for NACL or NACL entries, this is a strictly cfnlite
addition.

<a name="cfnsmart"></a>
##### cfnlite gets smart
A lot of the problems that cfnlite tries to resolve are around the verbosity
and repetitive nature of CFN. In that regard cfnlite tries to relieve some of
that burden off the developer. This is better illustrated with an example:
```yaml
name: cfnLiteVpcConnectIgwSimpleExample
resources:
  vpc:
    tags:
      name: microservice vpc
  internetGateway:
    tags:
      name: public gatway
```
Generates the following
```yaml
Resources:
  cfnLiteVpcConnectIgwSimpleExampleINTERNETGATEWAY:
    Properties:
      Tags:
        - Key: default-cfnlite-resource-name
          Value: cfnLiteVpcConnectIgwSimpleExampleINTERNETGATEWAY
        - Key: name
          Value: public gatway
    Type: AWS::EC2::InternetGateway

  cfnLiteVpcConnectIgwSimpleExampleINTERNETGATEWAYAttachement:
    Properties:
      InternetGatewayId: !Ref 'cfnLiteVpcConnectIgwSimpleExampleINTERNETGATEWAY'
      VpcId: !Ref 'cfnLiteVpcConnectIgwSimpleExampleVPC'
    Type: AWS::EC2::VPCGatewayAttachment

  cfnLiteVpcConnectIgwSimpleExampleVPC:
    Properties:
      CidrBlock: 10.0.0.0/16
      Tags:
        - Key: default-cfnlite-resource-name
          Value: cfnLiteVpcConnectIgwSimpleExampleVPC
        - Key: name
          Value: microservice vpc
    Type: AWS::EC2::VPC
```
The key thing worth highlight here is how we only needed define the internet
gateway and VPC resources and we got the `VPCGatewatAttachment` resource for
free. This is because as part of the IGW creation, cfnlite searches for a VPC
definition, if found it automatically creates the attachment resource.

Any network resource that needs a complimentary attachment reseource will
typically search for it and generate the attachment, this includes:
- subnet -> route table
- subnet -> NACL
- route table -> IGW
- IGW -> VPC

<a name="fullnet"></a>
##### Full network example
On average cfnlite is 3x - 5x less lines of code than its corresponding CFN.
The best example to really demonstrate this is a simple networking example which
configures a VPC with a bastion EC2 host.
```yaml
name: cfnLiteNetworkingExample
resources:
  vpc:
    cidrBlock: "10.0.0.0/16"
  internetGateway:
    tags:
      env: stage
      vpc-id: ref vpc
  networkAcl:
    ingress: [http, https, icmp, ssh]
    egress: [http, https, icmp]
    tags:
      env: prod
  routetable:
    dependsOn: ref vpc
    vpcId: ref vpc
    tags:
      env: prod
      vpc-id: ref vpc
  ec2:
    subnetId: ref vpc
    tags:
      name: bastion host
      vpc-id: ref vpc
  subnet:
    availabilityZone: eu-west-2b
    tags:
      name: subnet
      vpc-id: ref vpc
  securitygroups:
    GroupDescription: Handle inbound and outbound traffic
    securitygroupIngress: [http]
    securitygroupEgress: [http]
    vpcId: ref vpc
```
Generates (wait for it), over 5x as much CFN config code which would
normally be written by hand:
```yaml
Resources:
  cfnLiteNetworkingExampleEC2:
    Properties:
      ImageId: ami-0b45ae66668865cd6
      InstanceType: t2.micro
      SecurityGroups:
        - default
      SubnetId: !Ref 'cfnLiteNetworkingExampleVPC'
      Tags:
        - Key: default-cfnlite-resource-name
          Value: cfnLiteNetworkingExampleEC2
        - Key: name
          Value: bastion host
        - Key: vpc-id
          Value: !Ref 'cfnLiteNetworkingExampleVPC'
    Type: AWS::EC2::Instance
  cfnLiteNetworkingExampleINTERNETGATEWAY:
    Properties:
      Tags:
        - Key: default-cfnlite-resource-name
          Value: cfnLiteNetworkingExampleINTERNETGATEWAY
        - Key: env
          Value: stage
        - Key: vpc-id
          Value: !Ref 'cfnLiteNetworkingExampleVPC'
    Type: AWS::EC2::InternetGateway
  cfnLiteNetworkingExampleINTERNETGATEWAYAttachement:
    Properties:
      InternetGatewayId: !Ref 'cfnLiteNetworkingExampleINTERNETGATEWAY'
      VpcId: !Ref 'cfnLiteNetworkingExampleVPC'
    Type: AWS::EC2::VPCGatewayAttachment
  cfnLiteNetworkingExampleNETWORKACL:
    Properties:
      Tags:
        - Key: default-cfnlite-resource-name
          Value: cfnLiteNetworkingExampleNETWORKACL
        - Key: env
          Value: prod
      VpcId: id-example-vpc
    Type: AWS::EC2::NetworkAcl
  cfnLiteNetworkingExampleNETWORKACLRuleHTTPIn:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: false
      NetworkAclId: !Ref 'cfnLiteNetworkingExampleNETWORKACL'
      PortRange:
        From: 80
        To: 80
      Protocol: 6
      RuleAction: allow
      RuleNumber: 80
    Type: AWS::EC2::NetworkAclEntry
  cfnLiteNetworkingExampleNETWORKACLRuleHTTPOut:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: true
      NetworkAclId: !Ref 'cfnLiteNetworkingExampleNETWORKACL'
      PortRange:
        From: 80
        To: 80
      Protocol: 6
      RuleAction: allow
      RuleNumber: 80
    Type: AWS::EC2::NetworkAclEntry
  cfnLiteNetworkingExampleNETWORKACLRuleHTTPSIn:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: false
      NetworkAclId: !Ref 'cfnLiteNetworkingExampleNETWORKACL'
      PortRange:
        From: 443
        To: 443
      Protocol: 6
      RuleAction: allow
      RuleNumber: 443
    Type: AWS::EC2::NetworkAclEntry
  cfnLiteNetworkingExampleNETWORKACLRuleHTTPSOut:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: true
      NetworkAclId: !Ref 'cfnLiteNetworkingExampleNETWORKACL'
      PortRange:
        From: 443
        To: 443
      Protocol: 6
      RuleAction: allow
      RuleNumber: 443
    Type: AWS::EC2::NetworkAclEntry
  cfnLiteNetworkingExampleNETWORKACLRuleICMPIn:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: false
      Icmp:
        Code: 0
        Type: 8
      NetworkAclId: !Ref 'cfnLiteNetworkingExampleNETWORKACL'
      Protocol: 1
      RuleAction: allow
      RuleNumber: 100
    Type: AWS::EC2::NetworkAclEntry
  cfnLiteNetworkingExampleNETWORKACLRuleICMPOut:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: true
      Icmp:
        Code: 0
        Type: 0
      NetworkAclId: !Ref 'cfnLiteNetworkingExampleNETWORKACL'
      Protocol: 1
      RuleAction: allow
      RuleNumber: 100
    Type: AWS::EC2::NetworkAclEntry
  cfnLiteNetworkingExampleNETWORKACLRuleSSHIn:
    Properties:
      CidrBlock: '0.0.0.0/0'
      Egress: false
      NetworkAclId: !Ref 'cfnLiteNetworkingExampleNETWORKACL'
      PortRange:
        From: 22
        To: 22
      Protocol: 6
      RuleAction: allow
      RuleNumber: 22
    Type: AWS::EC2::NetworkAclEntry
  cfnLiteNetworkingExampleROUTETABLE:
    DependsOn: !Ref 'cfnLiteNetworkingExampleVPC'
    Properties:
      Tags:
        - Key: default-cfnlite-resource-name
          Value: cfnLiteNetworkingExampleROUTETABLE
        - Key: env
          Value: prod
        - Key: vpc-id
          Value: !Ref 'cfnLiteNetworkingExampleVPC'
      VpcId: !Ref 'cfnLiteNetworkingExampleVPC'
    Type: AWS::EC2::RouteTable
  cfnLiteNetworkingExampleROUTETABLERouteToIGW:
    Properties:
      DestinationCidrBlock: '0.0.0.0/0'
      GatewayId: !Ref 'cfnLiteNetworkingExampleINTERNETGATEWAY'
      RouteTableId: !Ref 'cfnLiteNetworkingExampleROUTETABLE'
    Type: AWS::EC2::Route
  cfnLiteNetworkingExampleSECURITYGROUPS:
    Properties:
      GroupDescription: Handle inbound and outbound traffic
      SecurityGroupEgress:
        - Properties:
            CidrIp: '0.0.0.0/0'
            Description: Outbound HTTP traffic
            FromPort: 80
            GroupId: !GetAtt 'cfnLiteNetworkingExampleSECURITYGROUPS.GroupId'
            IpProtocol: tcp
            ToPort: 80
          Type: AWS::EC2::SecurityGroupEgress
      SecurityGroupIngress:
        - Properties:
            CidrIp: '0.0.0.0/0'
            Description: Inbound HTTP traffic
            FromPort: 80
            GroupId: !GetAtt 'cfnLiteNetworkingExampleSECURITYGROUPS.GroupId'
            IpProtocol: tcp
            ToPort: 80
          Type: AWS::EC2::SecurityGroupIngress
      VpcId: !Ref 'cfnLiteNetworkingExampleVPC'
    Type: AWS::EC2::SecurityGroup
  cfnLiteNetworkingExampleSUBNET:
    Properties:
      AvailabilityZone: eu-west-2b
      CidrBlock: 10.0.1.0/24
      Tags:
        - Key: default-cfnlite-resource-name
          Value: cfnLiteNetworkingExampleSUBNET
        - Key: name
          Value: subnet
        - Key: vpc-id
          Value: !Ref 'cfnLiteNetworkingExampleVPC'
      VpcId: fake-vpc-id
    Type: AWS::EC2::Subnet
  cfnLiteNetworkingExampleSUBNETSubnetToNACL:
    Properties:
      NetworkAclId: !Ref 'cfnLiteNetworkingExampleNETWORKACL'
      SubnetId: !Ref 'cfnLiteNetworkingExampleSUBNET'
    Type: AWS::EC2::SubnetNetworkAclAssociation
  cfnLiteNetworkingExampleSUBNETSubnetToRouteTable:
    Properties:
      RouteTableId: !Ref 'cfnLiteNetworkingExampleROUTETABLE'
      SubnetId: !Ref 'cfnLiteNetworkingExampleSUBNET'
    Type: AWS::EC2::SubnetRouteTableAssociation
  cfnLiteNetworkingExampleVPC:
    Properties:
      CidrBlock: 10.0.0.0/16
    Type: AWS::EC2::VPC
```
