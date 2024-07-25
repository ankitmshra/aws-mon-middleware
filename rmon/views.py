import os
import json

from django.conf import settings
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
Region, RDSInstance, EC2Snapshot

from .serializers import IAMUserSerializer, S3BucketSerializer, \
RegionSerializer, RegionResourceCountSerializer, ResourceDetailSerializer, \
EC2InstanceSerializer, RDSInstanceSerializer, EBSVolumeSerializer, \
RDSSnapshotSerializer, EC2SnapshotSerializer, ElasticIPSerializer

class UpdateDataView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request, *args, **kwargs):
        (data, fetch_status) = fj(settings.AWS_ACCESS_KEY, 
        settings.AWS_SECRET_ACCESS_KEY, 
                                  settings.AWS_REGION, settings.BUCKET_NAME, 
                                  settings.OBJECT_KEY)
        
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

            # Update resources per region
            for region_name, resources in json_data.items():
                if region_name in ["global", "account_id", "project_name"]:
                    continue

                region, created = Region.objects.get_or_create(name=region_name)

                # Stopped EC2 Instances
                region.stopped_ec2_instances.clear()  # Clear existing relations
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
                            "potential_cost_savings": ec2_instance["PotentialCostSavings"],
                            "recommendations": ec2_instance["Recommendations"]
                        }
                    )
                    region.stopped_ec2_instances.add(instance)

                # Unused RDS Instances
                region.unused_rds_instances.clear()  # Clear existing relations
                for rds_instance in resources.get("UnusedRDSInstances", []):
                    instance, _ = RDSInstance.objects.get_or_create(
                        db_instance_identifier=rds_instance["DBInstanceIdentifier"],
                        defaults={
                            "db_instance_class": rds_instance["DBInstanceClass"],
                            "backup_type": rds_instance["BackupType"],
                            "region": rds_instance["Region"],
                            "potential_cost_savings": rds_instance["PotentialCostSavings"],
                            "recommendations": rds_instance["Recommendations"]
                        }
                    )
                    region.unused_rds_instances.add(instance)

                # Available EBS Volumes
                region.available_ebs_volumes.clear()  # Clear existing relations
                for ebs_volume in resources.get("AvailableEBSVolumes", []):
                    volume, _ = EBSVolume.objects.get_or_create(
                        volume_id=ebs_volume["VolumeId"],
                        defaults={
                            "size": ebs_volume["Size"],
                            "status": ebs_volume["Status"],
                            "region": ebs_volume["Region"],
                            "tags": ebs_volume["Tags"],
                            "potential_cost_savings": ebs_volume["PotentialCostSavings"],
                            "recommendations": ebs_volume["Recommendations"]
                        }
                    )
                    region.available_ebs_volumes.add(volume)

                # Old RDS Snapshots
                region.old_rds_snapshots.clear()  # Clear existing relations
                for rds_snapshot in resources.get("OldRDSSnapshots", []):
                    snapshot, _ = RDSSnapshot.objects.get_or_create(
                        snapshot_id=rds_snapshot["SnapshotId"],
                        defaults={
                            "creation_date": rds_snapshot["CreationDate"],
                            "region": rds_snapshot["Region"],
                            "potential_cost_savings": rds_snapshot["PotentialCostSavings"],
                            "recommendations": rds_snapshot["Recommendations"]
                        }
                    )
                    region.old_rds_snapshots.add(snapshot)

                # Old EC2 Snapshots
                region.old_ec2_snapshots.clear()  # Clear existing relations
                for ec2_snapshot in resources.get("OldEC2Snapshots", []):
                    snapshot, _ = EC2Snapshot.objects.get_or_create(
                        snapshot_id=ec2_snapshot["SnapshotId"],
                        defaults={
                            "creation_date": ec2_snapshot["CreationDate"],
                            "region": ec2_snapshot["Region"],
                            "potential_cost_savings": ec2_snapshot["PotentialCostSavings"],
                            "recommendations": ec2_snapshot["Recommendations"]
                        }
                    )
                    region.old_ec2_snapshots.add(snapshot)

                # Unused Elastic IPs
                region.unused_elastic_ips.clear()  # Clear existing relations
                for elastic_ip in resources.get("UnusedElasticIPs", []):
                    eip, _ = ElasticIP.objects.get_or_create(
                        allocation_id=elastic_ip["AllocationId"],
                        defaults={
                            "public_ip": elastic_ip["PublicIp"],
                            "region": elastic_ip["Region"],
                            "tags": elastic_ip["Tags"],
                            "potential_cost_savings": elastic_ip["PotentialCostSavings"],
                            "recommendations": elastic_ip["Recommendations"],
                            "age": elastic_ip["Age"]
                        }
                    )
                    region.unused_elastic_ips.add(eip)

            return Response({"message": "Data saved successfully."}, status=200)
        
        else:
            return Response({"data": data}, status=status.HTTP_401_UNAUTHORIZED)

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
