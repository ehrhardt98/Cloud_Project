import boto3
from botocore.exceptions import ClientError
from os import path, chmod
import time

Owner_name = 'Jorgg'
Key_name_v = 'Jorg_APS3_Key_virginia'
Key_name_o = 'Jorg_APS3_Key_ohio'
Group_name_v = 'Jorg_APS3_Group_virginia'
Group_name_o = 'Jorg_APS3_Group_ohio'
Mongo_group_name = 'Jorg_APS3_Mongo_Group'
Instance_type = 't2.micro'
ubuntu_image_id_Virginia = 'ami-04b9e92b5572fa0d1'
Ubuntu_image_id_Ohio = 'ami-0d5d9d301c853a04a'
Instance_name = 'Jorg_APS3_Instance'
LB_name = "JorgAPS3LB"
TG_name = "JorgAPS3TG"
image_name = 'Jorg_APS3_Instance_AMI'
LC_name = 'JorgAPS3LC'
AS_name = 'JorgAPS3AS'
availability_zone = 'us-east-1a'

auto_client_v = boto3.client('autoscaling', region_name='us-east-1')
ec2_client_v = boto3.client('ec2', region_name='us-east-1')
ec2_resource_v = boto3.resource('ec2', region_name='us-east-1')
elb_client_v = boto3.client('elbv2', region_name='us-east-1')


ec2_client_o = boto3.client('ec2', region_name='us-east-2')
ec2_resource_o = boto3.resource('ec2', region_name='us-east-2')


user_data_mongo = '''#! /bin/bash
                    sudo apt update
                    wget -qO - https://www.mongodb.org/static/pgp/server-4.2.asc | sudo apt-key add -
                    sudo apt-get install gnupg
                    wget -qO - https://www.mongodb.org/static/pgp/server-4.2.asc | sudo apt-key add -
                    echo "deb [ arch=amd64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.2 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.2.list
                    sudo apt-get update
                    sudo apt-get install -y mongodb-org
                    echo "mongodb-org hold" | sudo dpkg --set-selections
                    echo "mongodb-org-server hold" | sudo dpkg --set-selections
                    echo "mongodb-org-shell hold" | sudo dpkg --set-selections
                    echo "mongodb-org-mongos hold" | sudo dpkg --set-selections
                    echo "mongodb-org-tools hold" | sudo dpkg --set-selections
                    sudo sed -i "s,\\(^[[:blank:]]*bindIp:\\) .*,\\1 0.0.0.0," /etc/mongod.conf
                    sudo service mongod start'''

user_data_webserver_mongo = '''#! /bin/bash
                    sudo apt update
                    sudo apt install -y python3-pip
                    pip3 install pymongo
                    pip3 install fastapi
                    pip3 install pydantic==0.32.2
                    pip3 install uvicorn
                    pip3 install requests -y
                    echo "export PATH=\"\$PATH:/home/ubuntu/.local/bin/\"" >> ~/.bashrc
                    source ~/.bashrc
                    cd home/ubuntu
                    mkdir projeto_cloud
                    cd projeto_cloud
                    git clone https://github.com/ehrhardt98/Cloud_APS1
                    cd Cloud_APS1
                    export mongodb_ip={}
                    uvicorn main:app --port 5000 --host 0.0.0.0 --reload &
                    curl 127.0.0.1:5000'''

user_data_redirection = '''#! /bin/bash
                    sudo apt update
                    sudo apt install -y python3-pip
                    pip3 install fastapi
                    pip3 install pydantic==0.32.2
                    pip3 install uvicorn
                    pip3 install requests -y
                    echo "export PATH=\"\$PATH:/home/ubuntu/.local/bin/\"" >> ~/.bashrc
                    source ~/.bashrc
                    cd home/ubuntu
                    mkdir projeto_cloud
                    cd projeto_cloud
                    git clone https://github.com/ehrhardt98/Cloud_APS1
                    cd Cloud_APS1
                    export redirect_ip={}
                    uvicorn redirect:app --port 5000 --host 0.0.0.0 --reload &
                    curl 127.0.0.1:5000'''


def delete_KP(Key_name, ec2_client):
    print('Trying to delete key pair {}'.format(Key_name))
    try:
        ec2_client.describe_key_pairs(KeyNames=[Key_name])
        ec2_client.delete_key_pair(KeyName=Key_name)
        print('Key pair deleted')
    except:
        print('No Key Pair with that name')

def create_KP(Key_name, ec2_client):

    Key_path = Key_name + ".pem"

    print('Generating new Key Pair')

    key = ec2_client.create_key_pair(KeyName=Key_name)

    if (path.exists(Key_path)):
        chmod(Key_path, 0o777)

    with open(Key_path, "w+") as file:
        file.write(key['KeyMaterial'])

    chmod(Key_path, 0o400)

    print('New Key Pair generated successfully')

    return key

def delete_SG(Group_name, ec2_client):

    print('Trying to delete Security Group {}'.format(Group_name))
    try:
        ec2_client.describe_security_groups(
            GroupNames=[Group_name]
            )
        ec2_client.delete_security_group(
            GroupName=Group_name
            )
        print('Security Group deleted')
    except:
        print('No Security Group with that name')

def create_SG(Group_name, port, ec2_client):

    print('Generating new Security Group')

    response = ec2_client.describe_vpcs()

    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

    try:
        group = ec2_client.create_security_group(
            GroupName=Group_name, 
            Description=Group_name, 
            VpcId=vpc_id
        )

        security_group_id = group['GroupId']

        ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                {'IpProtocol': 'tcp',
                'FromPort': port,
                'ToPort': port,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])
        
        print('New Security Group generated successfully')

    except:
        print('Unable to create Security Group')

def create_empty_SG(Group_name, ec2_client):

    print('Generating new empty Security Group')

    response = ec2_client.describe_vpcs()

    vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

    try:
        ec2_client.create_security_group(
            GroupName=Group_name, 
            Description=Group_name, 
            VpcId=vpc_id
        )

        security_group_id = group['GroupId']

        ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                'FromPort': 27017,
                'ToPort': 27017,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])
        
        print('New  empty Security Group generated successfully')

    except:
        print('Unable to create empty Security Group')

def delete_instances(Key_name, ec2_client):

    print('Deleting all instances from Jorgg')

    instance_ids = []

    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'tag:Owner',
                'Values': [
                    'Jorgg',
                ]
            },
        ]
    )

    reservations = response['Reservations']

    for i in reservations:
        for j in i['Instances']:
            if j['State']['Name'] != 'terminated' and j['KeyName'] == Key_name:
                instance_ids.append(j['InstanceId'])

    if len(instance_ids) != 0:
        ec2_client.terminate_instances(
            InstanceIds = instance_ids
        )

        print('Waiting for instances to terminate')

        waiter = ec2_client.get_waiter('instance_terminated')
        waiter.wait(
            InstanceIds = instance_ids
        )

def create_instance(Ubuntu_image_id, Key_name, Group_name, Instance_name, user_data, ec2_client, ec2_resource):

    print('Creating instance {}'.format(Instance_name))
    
    instance = ec2_resource.create_instances(
        ImageId=Ubuntu_image_id,
        MinCount=1,
        MaxCount=1,
        KeyName=Key_name,
        SecurityGroups=[Group_name],
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Owner',
                        'Value': Owner_name
                    },
                    {
                        'Key': 'Name',
                        'Value': Instance_name
                    },
                ]
            },
        ],
        InstanceType=Instance_type,
        UserData=user_data
    )

    print('Waiting for instance to initialize')

    ids = []
    for i in instance:
        ids.append(i.id)

    waiter_instance = ec2_client.get_waiter('instance_status_ok')
    waiter_instance.wait(
        InstanceIds=ids
    )

    describe = ec2_client.describe_instances(
        InstanceIds = ids
    )

    instance_ip = describe['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['PrivateIpAddresses'][0]['PrivateIpAddress']
    # instance_ip = describe['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp']

    print('Instance initialized')

    return instance_ip

def create_redirection_instance(Ubuntu_image_id, Key_name, Group_name, Instance_name, user_data, Ohio_group_name, port, redirect_ip, ec2_client_v, ec2_resource, ec2_client_o):

    print('Creating redirection instance')
    
    instance = ec2_resource.create_instances(
        ImageId=Ubuntu_image_id,
        MinCount=1,
        MaxCount=1,
        KeyName=Key_name,
        SecurityGroups=[Group_name],
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Owner',
                        'Value': Owner_name
                    },
                    {
                        'Key': 'Name',
                        'Value': Instance_name
                    },
                ]
            },
        ],
        InstanceType=Instance_type,
        UserData=user_data.format(redirect_ip)
    )

    print('Waiting for redirection instance to initialize')

    ids = []
    for i in instance:
        ids.append(i.id)

    waiter_instance = ec2_client_v.get_waiter('instance_status_ok')
    waiter_instance.wait(
        InstanceIds=ids
    )

    describe = ec2_client_v.describe_instances(
        InstanceIds = ids
    )

    instance_ip = describe['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp']

    ec2_client_o.authorize_security_group_ingress(
            GroupName=Ohio_group_name,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                'FromPort': port,
                'ToPort': port,
                'IpRanges': [{'CidrIp': instance_ip+'/32'}]}
            ])
    
    ec2_client_o.revoke_security_group_ingress(
            GroupName=Ohio_group_name,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                'FromPort': 27017,
                'ToPort': 27017,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])

    print('Redirection Instance initialized')

    return instance_ip

def create_mongo_WS(Ubuntu_image_id, Key_name, Group_name, Instance_name, user_data, Mongo_group_name, port, redirect_ip, ec2_client, ec2_resource):

    print('Creating Mongo Webserver')
    
    instance = ec2_resource.create_instances(
        ImageId=Ubuntu_image_id,
        MinCount=1,
        MaxCount=1,
        KeyName=Key_name,
        SecurityGroups=[Group_name],
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Owner',
                        'Value': Owner_name
                    },
                    {
                        'Key': 'Name',
                        'Value': Instance_name
                    },
                ]
            },
        ],
        InstanceType=Instance_type,
        UserData=user_data.format(redirect_ip)
    )

    print('Waiting for Mongo Webserver instance to initialize')

    ids = []
    for i in instance:
        ids.append(i.id)

    waiter_instance = ec2_client.get_waiter('instance_status_ok')
    waiter_instance.wait(
        InstanceIds=ids
    )

    describe = ec2_client.describe_instances(
        InstanceIds = ids
    )

    instance_ip = describe['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['Association']['PublicIp']
    private_ip = describe['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['PrivateIpAddresses'][0]['PrivateIpAddress']

    ec2_client.authorize_security_group_ingress(
            GroupName=Mongo_group_name,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                'FromPort': port,
                'ToPort': port,
                'IpRanges': [{'CidrIp': private_ip+'/32'}]}
            ])
    
    ec2_client.revoke_security_group_ingress(
            GroupName=Mongo_group_name,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                'FromPort': 27017,
                'ToPort': 27017,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])

    print('Mongo Webserver Instance initialized')

    return instance_ip

def delete_LB(LB_name, elb_client):

    print('Trying to delete Load Balancer {}'.format(LB_name))

    try:
        LB_arn = elb_client.describe_load_balancers(
            Names=[
                LB_name
            ]
        )["LoadBalancers"][0]['LoadBalancerArn']

        print('Waiting for Load Balancer to be deleted')

        LB_waiter = elb_client.get_waiter('load_balancers_deleted')

        elb_client.delete_load_balancer(
            LoadBalancerArn=LB_arn
        )

        LB_waiter.wait(
            LoadBalancerArns=[
                LB_arn
            ]
        )

        print('Load Balancer deleted successfully')

        time.sleep(20)
    except:
        print('Unable to delete Load Balancer')

def create_LB(LB_name, elb_client):

    print('Creating Load Balancer')

    lb = elb_client.create_load_balancer(
        Name=LB_name,
        Subnets=[
            "subnet-65c07202",
            "subnet-6f905151",
            "subnet-782d9356",
            "subnet-7c55e920",
            "subnet-a69ee8a9",
            "subnet-dfc28195"
        ],
        Scheme="internet-facing",
        Tags=[
            {
                'Key': 'Owner',
                'Value': Owner_name
            },
        ],
        Type='application',
        IpAddressType='ipv4'
    )

    print('Waiting for Load Balancer to initialize')

    waiter = elb_client.get_waiter('load_balancer_exists')
    waiter.wait(
        LoadBalancerArns=[
            lb['LoadBalancers'][0]['LoadBalancerArn']
        ]
    )

    time.sleep(20)

    print('Load Balancer initialized')

    return lb['LoadBalancers'][0]['LoadBalancerArn']

def delete_TG(TG_name, elb_client):

    print('Trying to delete Target Group {}'.format(TG_name))

    try:
        TGs = elb_client.describe_target_groups(
            Names=[
                TG_name,
            ]
        )

        TG_arn = TGs['TargetGroups'][0]['TargetGroupArn']

        try:
            elb_client.delete_target_group(
                TargetGroupArn=TG_arn
            )

            print('Target Group deleted')

        except ClientError as e:
            print(e)
    except:
        print('Unable to delete Target Group')
        
def create_TG(TG_name, ec2_client, elb_client):

    print('Creating new Target Group')

    vpcs = ec2_client.describe_vpcs()

    vpc_id = vpcs.get('Vpcs', [{}])[0].get('VpcId', '')

    elb_client.create_target_group(
        Name=TG_name,
        Protocol='HTTP',
        Port=5000,
        VpcId=vpc_id,
        HealthCheckProtocol='HTTP',
        HealthCheckPath='/projeto_cloud/Cloud_APS1/',
        TargetType='instance'
    )

    TGs = elb_client.describe_target_groups(
        Names=[
            TG_name,
        ]
    )

    TG_arn = TGs['TargetGroups'][0]['TargetGroupArn']

    print('Target Group created successfully')

    return TG_arn

def createListener(TG_arn, LB_arn, elb_client):

    print('Creating listener for Load Balancer')

    elb_client.create_listener(
        DefaultActions=[
            {
                'TargetGroupArn': TG_arn,
                'Type': 'forward',
            },
        ],
        LoadBalancerArn=LB_arn,
        Port=5000,
        Protocol='HTTP'
    )

    print('Load Balancer Listener created')

def delete_LC(LC_name, auto_client):

    print('Trying to delete Launch Configuration {}'.format(LC_name))

    try:
        auto_client.describe_launch_configurations(
            LaunchConfigurationNames=[
                LC_name
            ]
        )
        auto_client.delete_launch_configuration(
            LaunchConfigurationName=LC_name
        )

        print('Launch Configuration deleted')

    except:
        print('Unable to delete Launch Configuration')

def create_LC(LC_name, Ubuntu_image_id, Key_name, Group_name, Instance_type, user_data, redirect_ip, auto_client):

    print('Creating new Launch Configuration')

    auto_client.create_launch_configuration(
        LaunchConfigurationName=LC_name,
        ImageId=Ubuntu_image_id,
        KeyName=Key_name,
        SecurityGroups=[
            Group_name
        ],
        InstanceType=Instance_type,
        InstanceMonitoring={
            'Enabled': True
        },
        UserData = user_data.format(redirect_ip)
    )

    print('Launch Configuration created')

def delete_AS(AS_name, auto_client):

    print('Trying to delete Auto Scaling Group')

    try:
        auto_client.delete_auto_scaling_group(
            AutoScalingGroupName=AS_name,
            ForceDelete=True
        )

        a = True
        while a:
            describe = auto_client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[
                    AS_name
                ]
            )['AutoScalingGroups']

            if len(describe) == 0:
                a = False

            time.sleep(2)

        time.sleep(10)

        print('Auto Scaling Group deleted successfully')

    except:
        print('Unable to delete Auto Scaling Group')

def create_AS(AS_name, LC_name, TG_arn, auto_client):

    print('Creating new Launch Configuration')

    auto_client.create_auto_scaling_group(
        AutoScalingGroupName=AS_name,
        LaunchConfigurationName=LC_name,
        MinSize=1,
        MaxSize=5,
        DesiredCapacity=1,
        DefaultCooldown=60,
        TargetGroupARNs=[
            TG_arn
        ],
        AvailabilityZones=[
            availability_zone
        ],
        HealthCheckGracePeriod=120,
        Tags=[
            {
                'Key': 'Owner',
                'Value': 'Jorgg'
            },{
                'Key': 'Name',
                'Value': AS_name
            }
        ]
    )

    print('New Launch Configuration created successfully')


def LaunchOhio():
    delete_instances(Key_name_o, ec2_client_o)
    delete_KP(Key_name_o, ec2_client_o)
    delete_SG(Group_name_o, ec2_client_o)
    delete_SG(Mongo_group_name, ec2_client_o)
    create_KP(Key_name_o, ec2_client_o)
    create_empty_SG(Group_name_o, ec2_client_o)
    create_empty_SG(Mongo_group_name, ec2_client_o)
    mongo_ip = create_instance(Ubuntu_image_id_Ohio, Key_name_o, Mongo_group_name, 'Mongo_ohio', user_data_mongo, ec2_client_o, ec2_resource_o)
    mongo_webserver_ip = create_mongo_WS(Ubuntu_image_id_Ohio, Key_name_o, Group_name_o, 'Mongo_Webserver_ohio', user_data_webserver_mongo, Mongo_group_name, 27017, mongo_ip, ec2_client_o, ec2_resource_o)
    
    return mongo_webserver_ip

def LaunchVirginia(ohio_webserver_ip):

    delete_instances(Key_name_v, ec2_client_v)
    delete_AS(AS_name, auto_client_v)
    delete_LC(LC_name, auto_client_v)
    delete_LB(LB_name, elb_client_v)
    delete_TG(TG_name, elb_client_v)
    delete_KP(Key_name_v, ec2_client_v)
    create_KP(Key_name_v, ec2_client_v)
    delete_SG(Group_name_v, ec2_client_v)
    create_SG(Group_name_v, 5000, ec2_client_v)
    virginia_webserver_ip = create_redirection_instance(ubuntu_image_id_Virginia, Key_name_v, Group_name_v, Instance_name, user_data_redirection, Group_name_o, 5000, ohio_webserver_ip, ec2_client_v, ec2_resource_v, ec2_client_o)
    LB_arn = create_LB(LB_name, elb_client_v)
    TG_arn = create_TG(TG_name, ec2_client_v, elb_client_v)
    createListener(TG_arn, LB_arn, elb_client_v)
    create_LC(LC_name, ubuntu_image_id_Virginia, Key_name_v, Group_name_v, Instance_type, user_data_redirection, virginia_webserver_ip, auto_client_v)
    create_AS(AS_name, LC_name, TG_arn, auto_client_v)


if __name__ == '__main__':

    ohio_webserver_ip = LaunchOhio()

    LaunchVirginia(ohio_webserver_ip)