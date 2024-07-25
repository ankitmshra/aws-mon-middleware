import boto3
import json
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    print("Starting function execution")

    # Cost defined based on us-east-1 
    cost_per_ec2_instance = 0.0116  # USD per hour for a t2.micro instance
    cost_per_gb_ebs = 0.10  # USD per GB per month for EBS
    cost_per_rds_instance = 0.038  # USD per hour for a db.t2.micro instance
    cost_per_gb_rds_snapshot = 0.125  # USD per GB per month for RDS snapshots
    cost_per_gb_ebs_snapshots = 0.10  # USD per GB per month for EBS snapshots
    cost_per_elastic_ip = 0.005  # USD per hour for an unused Elastic IP

    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']
    print(f"Account ID: {account_id}")

    ec2 = boto3.client('ec2')
    all_regions = [region['RegionName'] for region in ec2.describe_regions()['Regions']]
    print(f"Regions to check: {all_regions}")

    output = {'project_name': 'Cloud Efficiency Explorer', 'account_id': account_id, 'global': {}}

    s3_client = boto3.client('s3')
    cloudwatch_client = boto3.client('cloudwatch')
    iam_client = boto3.client('iam')

    # Get last login details of IAM users
    print("Getting last login details of IAM users who have not logged in for more than 2 days")
    users = iam_client.list_users()
    iam_user_info = []
    two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
    for user in users['Users']:
        user_info = {
            'UserId': user['UserId'],
            'UserName': user['UserName'],
            'Tags': user.get('Tags', [])
        }
        try:
            login_profile = iam_client.get_login_profile(UserName=user['UserName'])
            last_login = login_profile['LoginProfile']['CreateDate']
            if last_login < two_days_ago:
                user_info['LastLogin'] = last_login.strftime("%Y-%m-%d %H:%M:%S")
                iam_user_info.append(user_info)
        except iam_client.exceptions.NoSuchEntityException:
            # User has never logged in
            user_info['LastLogin'] = 'Never logged in'
            iam_user_info.append(user_info)

    output['global']['IAMUsers'] = iam_user_info
    print(f"IAM user info: {iam_user_info}")

    # List all empty and unused S3 buckets
    print("Listing all empty and unused S3 buckets")
    all_buckets = s3_client.list_buckets()
    s3_bucket_info = []
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)

    for bucket in all_buckets['Buckets']:
        bucket_info = {
            'BucketName': bucket['Name'],
            'CreationDate': bucket['CreationDate'].strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            bucket_info['Tags'] = s3_client.get_bucket_tagging(Bucket=bucket['Name']).get('TagSet', [])
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchTagSet':
                bucket_info['Tags'] = []
            else:
                raise
        objects = s3_client.list_objects_v2(Bucket=bucket['Name'])
        if 'Contents' not in objects:
            bucket_info['Status'] = 'Empty'
            s3_bucket_info.append(bucket_info)
        else:
            response_objects = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName='NumberOfObjects',
                Dimensions=[
                    {'Name': 'BucketName', 'Value': bucket['Name']},
                    {'Name': 'StorageType', 'Value': 'AllStorageTypes'}
                ],
                StartTime=one_day_ago,
                EndTime=datetime.now(timezone.utc),
                Period=86400,
                Statistics=['Average']
            )
            response_size = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName='BucketSizeBytes',
                Dimensions=[
                    {'Name': 'BucketName', 'Value': bucket['Name']},
                    {'Name': 'StorageType', 'Value': 'StandardStorage'}
                ],
                StartTime=one_day_ago,
                EndTime=datetime.now(timezone.utc),
                Period=86400,
                Statistics=['Average']
            )
            if all([datapoint['Average'] == 0 for datapoint in response_objects['Datapoints']]) and all([datapoint['Average'] == 0 for datapoint in response_size['Datapoints']]):
                bucket_info['Status'] = 'Unused'
                s3_bucket_info.append(bucket_info)

    output['global']['S3Buckets'] = s3_bucket_info
    print(f"S3 bucket info: {s3_bucket_info}")

    # initialized cumulative cost values are assigned for calculating
    cumulative_costs = {
        'EC2': 0,
        'RDS': 0,
        'EBS': 0,
        'RDSSnapshots': 0,
        'EBSSnapshots': 0,
        'ElasticIPs': 0
    }

    for region in all_regions:
        print(f"Checking region: {region}")
        ec2_client = boto3.client('ec2', region_name=region)
        rds_client = boto3.client('rds', region_name=region)
        cloudwatch_client = boto3.client('cloudwatch', region_name=region)
        print("Listing all stopped EC2 instances")
        stopped_ec2 = ec2_client.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}]
        )
        stopped_ec2_instances = []
        for reservation in stopped_ec2['Reservations']:
            for instance in reservation['Instances']:
                instance_info = {
                    'InstanceId': instance['InstanceId'],
                    'InstanceType': instance['InstanceType'],
                    'LaunchTime': instance['LaunchTime'].strftime("%Y-%m-%d %H:%M:%S"),
                    'Region': region,
                    'Age': (datetime.now(timezone.utc) - instance['LaunchTime']).days,
                    'Tags': instance.get('Tags', []),
                    'Status': 'stopped',
                    'PotentialCostSavings': f"{cost_per_ec2_instance * 24 * 30:.2f} USD",  # Assuming 30 days of potential savings
                    'Recommendations': f"Need to save cost? Review and delete this resource: https://console.aws.amazon.com/ec2/v2/home?region={region}#Instances:instanceId={instance['InstanceId']}\nNeed to create cleanup ticket for this resource? https://cuda.atlassian.net/jira/"
                }
                stopped_ec2_instances.append(instance_info)
                cumulative_costs['EC2'] += cost_per_ec2_instance * 24 * 30


        print("Listing all unused RDS instances")
        rds_instances = rds_client.describe_db_instances()
        unused_rds = []
        for db in rds_instances['DBInstances']:
            response = cloudwatch_client.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='DatabaseConnections',
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db['DBInstanceIdentifier']}],
                StartTime=one_day_ago,
                EndTime=datetime.now(timezone.utc),
                Period=86400,
                Statistics=['Average']
            )
            if all([datapoint['Average'] == 0 for datapoint in response['Datapoints']]):
                db_info = {
                    'DBInstanceIdentifier': db['DBInstanceIdentifier'],
                    'DBInstanceClass': db['DBInstanceClass'],
                    'BackupType': 'automated' if db.get('AutomatedBackups') else 'manual',
                    'Tags': db.get('TagList', []),
                    'Region': region,
                    'PotentialCostSavings': f"{cost_per_rds_instance * 24 * 30:.2f} USD",  # Assuming 30 days of potential savings
                    'Recommendations': f"Need to save cost? Review and delete this resource: https://console.aws.amazon.com/rds/home?region={region}#dbinstances:id={db['DBInstanceIdentifier']}\nNeed to create cleanup ticket for this resource? https://cuda.atlassian.net/jira/"
                }
                unused_rds.append(db_info)
                cumulative_costs['RDS'] += cost_per_rds_instance * 24 * 30

    
        print("Listing all available EBS volumes")
        volumes = ec2_client.describe_volumes(Filters=[{'Name': 'status', 'Values': ['available']}])
        available_volumes_info = []
        for volume in volumes['Volumes']:
            volume_info = {
                'VolumeId': volume['VolumeId'],
                'Size': volume['Size'],
                'Tags': volume.get('Tags', []),
                'Region': region,
                'PotentialCostSavings': f"{cost_per_gb_ebs * volume['Size']:.2f} USD",  # Assuming monthly cost
                'Recommendations': f"Need to save cost? Review and delete this resource: https://console.aws.amazon.com/ec2/v2/home?region={region}#Volumes:volumeId={volume['VolumeId']}\nNeed to create cleanup ticket for this resource? https://cuda.atlassian.net/jira/"
            }
            available_volumes_info.append(volume_info)
            cumulative_costs['EBS'] += cost_per_gb_ebs * volume['Size']

    
        print("Listing all old RDS snapshots")
        rds_snapshots = rds_client.describe_db_snapshots()
        old_rds_snapshots = []
        for snapshot in rds_snapshots['DBSnapshots']:
            if snapshot['SnapshotCreateTime'] < one_day_ago:
                snapshot_info = {
                    'DBSnapshotIdentifier': snapshot['DBSnapshotIdentifier'],
                    'SnapshotCreateTime': snapshot['SnapshotCreateTime'].strftime("%Y-%m-%d %H:%M:%S"),
                    'Region': region,
                    'Size': snapshot['AllocatedStorage'],
                    'Tags': snapshot.get('TagList', []),
                    'PotentialCostSavings': f"{cost_per_gb_rds_snapshot * snapshot['AllocatedStorage']:.2f} USD",  # Assuming monthly cost
                    'Recommendations': f"Need to save cost? Review and delete this resource: https://console.aws.amazon.com/rds/home?region={region}#dbsnapshots:id={snapshot['DBSnapshotIdentifier']}\nNeed to create cleanup ticket for this resource? https://cuda.atlassian.net/jira/"
                }
                old_rds_snapshots.append(snapshot_info)
                cumulative_costs['RDSSnapshots'] += cost_per_gb_rds_snapshot * snapshot['AllocatedStorage']


        print("Listing all old EBS snapshots")
        ebs_snapshots = ec2_client.describe_snapshots(OwnerIds=[account_id])
        old_ebs_snapshots = []
        for snapshot in ebs_snapshots['Snapshots']:
            if snapshot['StartTime'] < one_day_ago:
                snapshot_info = {
                    'SnapshotId': snapshot['SnapshotId'],
                    'StartTime': snapshot['StartTime'].strftime("%Y-%m-%d %H:%M:%S"),
                    'VolumeSize': snapshot['VolumeSize'],
                    'Tags': snapshot.get('Tags', []),
                    'Region': region,
                    'PotentialCostSavings': f"{cost_per_gb_ebs_snapshots * snapshot['VolumeSize']:.2f} USD",  # Assuming monthly cost
                    'Recommendations': f"Need to save cost? Review and delete this resource: https://console.aws.amazon.com/ec2/v2/home?region={region}#snapshots:snapshotId={snapshot['SnapshotId']}\nNeed to create cleanup ticket for this resource? https://cuda.atlassian.net/jira/"
                }
                old_ebs_snapshots.append(snapshot_info)
                cumulative_costs['EBSSnapshots'] += cost_per_gb_ebs_snapshots * snapshot['VolumeSize']

        print("Listing all available Elastic IPs")
        addresses = ec2_client.describe_addresses()
        available_elastic_ips = []
        for address in addresses['Addresses']:
            if address.get('AssociationId') is None:
                address_info = {
                    'AllocationId': address['AllocationId'],
                    'PublicIp': address['PublicIp'],
                    'Tags': address.get('Tags', []),
                    'Region': region,
                    'PotentialCostSavings': f"{cost_per_elastic_ip * 24 * 30:.2f} USD",  # Assuming 30 days of potential savings
                    'Recommendations': f"Need to save cost? Review and delete this resource: https://console.aws.amazon.com/ec2/v2/home?region={region}#Addresses:allocationId={address['AllocationId']}\nNeed to create cleanup ticket for this resource? https://cuda.atlassian.net/jira/"
                }
                available_elastic_ips.append(address_info)
                cumulative_costs['ElasticIPs'] += cost_per_elastic_ip * 24 * 30

        output[region] = {
            'StoppedEC2Instances': stopped_ec2_instances,
            'UnusedRDSInstances': unused_rds,
            'AvailableEBSVolumes': available_volumes_info,
            'OldRDSSnapshots': old_rds_snapshots,
            'OldEBSSnapshots': old_ebs_snapshots,
            'AvailableElasticIPs': available_elastic_ips
        }
    output['global']['CumulativeCostOptimization'] = {
        'EC2': f"{cumulative_costs['EC2']:.2f} USD",
        'RDS': f"{cumulative_costs['RDS']:.2f} USD",
        'EBS': f"{cumulative_costs['EBS']:.2f} USD",
        'RDSSnapshots': f"{cumulative_costs['RDSSnapshots']:.2f} USD",
        'EBSSnapshots': f"{cumulative_costs['EBSSnapshots']:.2f} USD",
        'ElasticIPs': f"{cumulative_costs['ElasticIPs']:.2f} USD"
    }
    print(f"Cumulative cost optimization: {output['global']['CumulativeCostOptimization']}")
    s3_output_key = 'output.json'
    s3_client.put_object(
        Bucket='unused-resources-output',
        Key=s3_output_key,
        Body=json.dumps(output, indent=4),
        ContentType='application/json'
    )
    print(f"Output saved to S3 bucket: {s3_output_key}")

    return output

