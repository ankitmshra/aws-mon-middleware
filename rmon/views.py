import os
import json

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.dateformat import format
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import filters
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.core.files.storage import FileSystemStorage
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from .helpers.fetch_json import fetch_json as fj
from .models import IAMUser, S3Bucket, EC2Instance, \
EBSVolume, RDSSnapshot, ElasticIP, \
Region, RDSInstance, EC2Snapshot, Project, \
CumulativeCost,CumulativeCostHistory

from .serializers import IAMUserSerializer, S3BucketSerializer, \
RegionSerializer, RegionResourceCountSerializer, ResourceDetailSerializer, \
EC2InstanceSerializer, RDSInstanceSerializer, EBSVolumeSerializer, \
RDSSnapshotSerializer, EC2SnapshotSerializer, ElasticIPSerializer, \
ProjectSerializer

from credman.models import AWSAccountCredentials as aac

class UpdateDataView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):

        try:
            # Retrieve AWS credentials for the user from the credman app
            aws_credentials = aac.objects.get(user=request.user)
        except aac.DoesNotExist:
            return Response({"error": "No AWS credentials found for the user."},
             status=status.HTTP_400_BAD_REQUEST)

        aws_access_key_id = aws_credentials.aws_access_key_id
        aws_secret_access_key = aws_credentials.aws_secret_access_key
        aws_region = aws_credentials.aws_region
        bucket_name = aws_credentials.bucket_name
        object_key = aws_credentials.object_key

        (data, fetch_status) = fj(aws_access_key_id, 
                                  aws_secret_access_key, 
                                  aws_region, 
                                  bucket_name, 
                                  object_key)
        
        if fetch_status:
            fs = FileSystemStorage(location=settings.STATIC_ROOT)
            directory = 'data'

            file_path = os.path.join(directory, 'data.json')
            full_directory_path = os.path.join(settings.STATIC_ROOT, directory)
            if not os.path.exists(full_directory_path):
                os.makedirs(full_directory_path)

            with fs.open(file_path, 'w') as file:
                file.write(data)

            json_data = json.loads(data)

            # Update IAM Users
            IAMUser.objects.all().delete()  # Clear existing records
            for user in json_data.get("global", {}).get("IAMUsers", []):
                IAMUser.objects.create(
                    user_id=user["UserId"],
                    user_name=user["UserName"],
                    tags=user["Tags"],
                    last_login=user["LastLogin"]
                )

            # Update S3 Buckets
            S3Bucket.objects.all().delete()  # Clear existing records
            for bucket in json_data.get("global", {}).get("S3Buckets", []):
                S3Bucket.objects.create(
                    bucket_name=bucket["BucketName"],
                    creation_date=bucket["CreationDate"],
                    tags=bucket["Tags"],
                    status=bucket["Status"],
                )

            self.update_cumulative_cost(json_data)

            # Update resources per region
            for region_name, resources in json_data.items():
                if region_name in ["global", "account_id", "project_name"]:
                    continue

                region, created = Region.objects.get_or_create(name=region_name)

                # Process each resource type
                self.update_ec2_instances(region, resources)
                self.update_rds_instances(region, resources)
                self.update_ebs_volumes(region, resources)
                self.update_rds_snapshots(region, resources)
                self.update_ec2_snapshots(region, resources)
                self.update_elastic_ips(region, resources)

            # Save project data
            self.update_project_data(request.user, json_data)

            return Response({"message": "Data saved successfully."}, status=200)
        
        else:
            return Response({"data": data}, status=status.HTTP_401_UNAUTHORIZED)

    def update_project_data(self, user, json_data):
        # Clear existing project records for the user
        Project.objects.filter(user=user).delete()
        Project.objects.create(
            user=user,
            project_name=json_data["project_name"],
            account_id=json_data["account_id"]
        )

    def update_cumulative_cost(self, json_data):
        # Extract cumulative costs
        cumulative_cost_data = json_data.get("global", {}).get("CumulativeCostOptimization", {})
        ec2_cost = cumulative_cost_data.get("EC2", "0.00 USD").replace(" USD", "")
        rds_cost = cumulative_cost_data.get("RDS", "0.00 USD").replace(" USD", "")
        ebs_cost = cumulative_cost_data.get("EBS", "0.00 USD").replace(" USD", "")
        rds_snapshots_cost = cumulative_cost_data.get("RDSSnapshots", "0.00 USD").replace(" USD", "")
        ebs_snapshots_cost = cumulative_cost_data.get("EBSSnapshots", "0.00 USD").replace(" USD", "")
        elastic_ips_cost = cumulative_cost_data.get("ElasticIPs", "0.00 USD").replace(" USD", "")

        # Save current cost to history
        CumulativeCostHistory.objects.create(
            ec2_cost=ec2_cost,
            rds_cost=rds_cost,
            ebs_cost=ebs_cost,
            rds_snapshots_cost=rds_snapshots_cost,
            ebs_snapshots_cost=ebs_snapshots_cost,
            elastic_ips_cost=elastic_ips_cost
        )

        # Update latest cumulative cost
        CumulativeCost.objects.update_or_create(
            defaults={
                'ec2_cost': ec2_cost,
                'rds_cost': rds_cost,
                'ebs_cost': ebs_cost,
                'rds_snapshots_cost': rds_snapshots_cost,
                'ebs_snapshots_cost': ebs_snapshots_cost,
                'elastic_ips_cost': elastic_ips_cost
            }
        )

    def update_ec2_instances(self, region, resources):
        # Stopped EC2 Instances
        region.stopped_ec2_instances.clear()
        for ec2_instance in resources.get("StoppedEC2Instances", []):
            instance, _ = EC2Instance.objects.get_or_create(
                instance_id=ec2_instance["InstanceId"],
                defaults={
                    "instance_type": ec2_instance["InstanceType"],
                    "launch_time": ec2_instance["LaunchTime"],
                    "region": ec2_instance["Region"],
                    "age": ec2_instance["Age"],
                    "tags": ec2_instance["Tags"],
                    "status": ec2_instance["Status"],
                    "potential_cost_savings": ec2_instance["PotentialCostSavings"].split(" ")[0],
                    "recommendations": ec2_instance["Recommendations"]
                }
            )
            region.stopped_ec2_instances.add(instance)

    def update_rds_instances(self, region, resources):
        # Unused RDS Instances
        region.unused_rds_instances.clear()
        for rds_instance in resources.get("UnusedRDSInstances", []):
            instance, _ = RDSInstance.objects.get_or_create(
                db_instance_identifier=rds_instance["DBInstanceIdentifier"],
                defaults={
                    "db_instance_class": rds_instance["DBInstanceClass"],
                    "backup_type": rds_instance["BackupType"],
                    "region": rds_instance["Region"],
                    "potential_cost_savings": rds_instance["PotentialCostSavings"].split(" ")[0],
                    "recommendations": rds_instance["Recommendations"]
                }
            )
            region.unused_rds_instances.add(instance)

    def update_ebs_volumes(self, region, resources):
        # Available EBS Volumes
        region.available_ebs_volumes.clear()
        for ebs_volume in resources.get("AvailableEBSVolumes", []):
            volume, _ = EBSVolume.objects.get_or_create(
                volume_id=ebs_volume["VolumeId"],
                defaults={
                    "size": ebs_volume["Size"],
                    "region": ebs_volume["Region"],
                    "tags": ebs_volume["Tags"],
                    "potential_cost_savings": ebs_volume["PotentialCostSavings"].split(" ")[0],
                    "recommendations": ebs_volume["Recommendations"]
                }
            )
            region.available_ebs_volumes.add(volume)

    def update_rds_snapshots(self, region, resources):
        # Old RDS Snapshots
        region.old_rds_snapshots.clear()
        for rds_snapshot in resources.get("OldRDSSnapshots", []):
            snapshot, _ = RDSSnapshot.objects.get_or_create(
                snapshot_id=rds_snapshot["SnapshotId"],
                defaults={
                    "creation_date": rds_snapshot["CreationDate"],
                    "region": rds_snapshot["Region"],
                    "potential_cost_savings": rds_snapshot["PotentialCostSavings"].split(" ")[0],
                    "recommendations": rds_snapshot["Recommendations"]
                }
            )
            region.old_rds_snapshots.add(snapshot)

    def update_ec2_snapshots(self, region, resources):
        # Old EC2 Snapshots
        region.old_ec2_snapshots.clear()
        for ec2_snapshot in resources.get("OldEBSSnapshots", []):
            snapshot, _ = EC2Snapshot.objects.get_or_create(
                snapshot_id=ec2_snapshot["SnapshotId"],
                defaults={
                    "creation_date": ec2_snapshot["StartTime"],
                    "region": ec2_snapshot["Region"],
                    "potential_cost_savings": ec2_snapshot["PotentialCostSavings"].split(" ")[0],
                    "recommendations": ec2_snapshot["Recommendations"]
                }
            )
            region.old_ec2_snapshots.add(snapshot)

    def update_elastic_ips(self, region, resources):
        # Unused Elastic IPs
        region.unused_elastic_ips.clear()
        for elastic_ip in resources.get("AvailableElasticIPs", []):
            eip, _ = ElasticIP.objects.get_or_create(
                allocation_id=elastic_ip["AllocationId"],
                defaults={
                    "public_ip": elastic_ip["PublicIp"],
                    "region": elastic_ip["Region"],
                    "tags": elastic_ip["Tags"],
                    "potential_cost_savings": elastic_ip["PotentialCostSavings"].split(" ")[0],
                    "recommendations": elastic_ip["Recommendations"],
                }
            )
            region.unused_elastic_ips.add(eip)

class IAMUserListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    queryset = IAMUser.objects.all()
    serializer_class = IAMUserSerializer

class S3BucketListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    queryset = S3Bucket.objects.all()
    serializer_class = S3BucketSerializer

class RegionDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    lookup_field = 'name'

class TotalResourceCountView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request, *args, **kwargs):
        try:
            regions = Region.objects.all()
            serializer = RegionResourceCountSerializer(regions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AllResourcesView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request, *args, **kwargs):
        # Fetch all resources
        ec2_instances = EC2Instance.objects.all()
        rds_instances = RDSInstance.objects.all()
        ebs_volumes = EBSVolume.objects.all()
        rds_snapshots = RDSSnapshot.objects.all()
        ec2_snapshots = EC2Snapshot.objects.all()
        elastic_ips = ElasticIP.objects.all()
        
        # Serialize data
        data = {
            'ec2_instances': EC2InstanceSerializer(ec2_instances, many=True).data,
            'rds_instances': RDSInstanceSerializer(rds_instances, many=True).data,
            'ebs_volumes': EBSVolumeSerializer(ebs_volumes, many=True).data,
            'rds_snapshots': RDSSnapshotSerializer(rds_snapshots, many=True).data,
            'ec2_snapshots': EC2SnapshotSerializer(ec2_snapshots, many=True).data,
            'elastic_ips': ElasticIPSerializer(elastic_ips, many=True).data
        }

        return Response(data, status=status.HTTP_200_OK)


class FetchAccountDetailsView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        # Fetch the user's projects
        projects = Project.objects.filter(user=request.user)
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=200)

class LatestCumulativeCostView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        try:
            # Get the latest cumulative cost record
            latest_cost = CumulativeCost.objects.latest('last_updated')
            data = {
                'ec2_cost': latest_cost.ec2_cost,
                'rds_cost': latest_cost.rds_cost,
                'ebs_cost': latest_cost.ebs_cost,
                'rds_snapshots_cost': latest_cost.rds_snapshots_cost,
                'ebs_snapshots_cost': latest_cost.ebs_snapshots_cost,
                'elastic_ips_cost': latest_cost.elastic_ips_cost,
                'last_updated': latest_cost.last_updated
            }
            return Response(data, status=200)
        except CumulativeCost.DoesNotExist:
            return Response(
                {"error": "No cumulative cost data available."}, 
            status=404)


class CumulativeCostRangeView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return Response(
                {"error": "Both 'start_date' and 'end_date' parameters are required."}
                , status=400)

        try:
            # Parse the date strings
            start_date = parse_datetime(start_date_str)
            end_date = parse_datetime(end_date_str)

            if start_date is None or end_date is None:
                return Response({"error": "Invalid date format."}, status=400)

            # Query the cumulative cost history within the date range
            cost_history = CumulativeCostHistory.objects.filter(
                recorded_at__range=[start_date, end_date])

            if not cost_history.exists():
                return Response(
                    {"message": "No data available for the given date range."}, 
                    status=404)

            # Initialize empty lists for each cost type
            data = {
                'ec2_cost': [],
                'rds_cost': [],
                'ebs_cost': [],
                'rds_snapshots_cost': [],
                'ebs_snapshots_cost': [],
                'elastic_ips_cost': []
            }

            # Populate the lists with data from the queried records
            for record in cost_history:
                data['ec2_cost'].append(record.ec2_cost)
                data['rds_cost'].append(record.rds_cost)
                data['ebs_cost'].append(record.ebs_cost)
                data['rds_snapshots_cost'].append(record.rds_snapshots_cost)
                data['ebs_snapshots_cost'].append(record.ebs_snapshots_cost)
                data['elastic_ips_cost'].append(record.elastic_ips_cost)

            return Response(data, status=200)

        except ValueError as e:
            return Response({"error": str(e)}, status=400)