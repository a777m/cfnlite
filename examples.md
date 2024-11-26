## Examples
Generally speaking, valid YAML is valid CFNLite. For a full list of properties supported on each resources
run `cfnlite --explain <resource-name>`

#### EC2
```yaml
name: cfnLiteEc2Example
resources:
  ec2:
    securityGroups:
      - default
```
The above example generates the following
```yaml
Resources:
  cfnLiteEc2ExampleEC2:
    Properties:
      ImageId: ami-0b45ae66668865cd6
      InstanceType: t2.micro
      SecurityGroups:
        - default
    Type: AWS::EC2::Instance
```
Of the cnflite supported AWS resources, this is probably the simplest example.
Each resource comes with defaults for all the required fields so you don't need
pass more property values than needed.

Some things to note:
- for each resource you do need to pass at least on property.
- cfnlite requires a name field, this is used as part of giving resources
unique names
- you can overwrite any of the supported properties
- if the property expects a list, you can pass single values as a string.
In the case above 'default' would be fine as a string.
- property names need not be PascalCase, they can be formatted however you see
fit (all still one word)
- Property names must match those of CloudFormation

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
