# Cloud_Project

Script for launching a cloud application in AWS using the boto3 SDK


This script launches instances in the North Virginia and Ohio regions to simulate the division between a Public and Private cloud.

In Ohio, the "Private" portion of the application, there are two instances, one running the MongoDB database and the other running its WebServer. Now in the Public portion, located in North Virginia, there are instances that redirect the requests they receive to Ohios WebServer, acting as a sort of VPN.

### Configuring the AWS environment

To run this script you'll need to install the AWS CLI:

*Note that you should use your correspondent pip version

`$ pip3 install awscli --upgrade --user`

Then you should be able to load in your Amazon account credentials:

```$ aws configure
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json
```

Now simply run the python file to launch the application:

`$ python3 Cloud_Project.py`

To check if it all worked out, get the load balancer's public DNS and write it into your browser as such:

`http://<load-balancer-DNS>:5000/docs`
