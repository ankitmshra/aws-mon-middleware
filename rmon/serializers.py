from rest_framework import serializers
from .models import IAMUser, S3Bucket, EC2Instance, \
EBSVolume, RDSSnapshot, ElasticIP, \
Region, RDSInstance, EC2Snapshot
class IAMUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = IAMUser
        fields = '__all__'

class S3BucketSerializer(serializers.ModelSerializer):
    class Meta:
        model = S3Bucket
        fields = '__all__'

class EC2InstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EC2Instance
        fields = '__all__'

class RDSInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDSInstance
        fields = '__all__'

class EBSVolumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EBSVolume
        fields = '__all__'

class RDSSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = RDSSnapshot
        fields = '__all__'

class EC2SnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = EC2Snapshot
        fields = '__all__'

class ElasticIPSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElasticIP
        fields = '__all__'

class RegionSerializer(serializers.ModelSerializer):
    stopped_ec2_instances = EC2InstanceSerializer(many=True)
    unused_rds_instances = RDSInstanceSerializer(many=True)
    available_ebs_volumes = EBSVolumeSerializer(many=True)
    old_rds_snapshots = RDSSnapshotSerializer(many=True)
    old_ec2_snapshots = EC2SnapshotSerializer(many=True)
    unused_elastic_ips = ElasticIPSerializer(many=True)

    class Meta:
        model = Region
        fields = '__all__'

class RegionResourceCountSerializer(serializers.ModelSerializer):
    total_resources = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = ['name', 'total_resources']

    def get_total_resources(self, obj):
        # Calculate the total count of all resources in this region
        total_count = (
            obj.stopped_ec2_instances.count() +
            obj.unused_rds_instances.count() +
            obj.available_ebs_volumes.count() +
            obj.old_rds_snapshots.count() +
            obj.old_ec2_snapshots.count() +
            obj.unused_elastic_ips.count()
        )
        return total_count
    
class ResourceDetailSerializer(serializers.Serializer):
    ec2_instances = EC2InstanceSerializer(many=True)
    rds_instances = RDSInstanceSerializer(many=True)
    ebs_volumes = EBSVolumeSerializer(many=True)
    rds_snapshots = RDSSnapshotSerializer(many=True)
    ec2_snapshots = EC2SnapshotSerializer(many=True)
    elastic_ips = ElasticIPSerializer(many=True)