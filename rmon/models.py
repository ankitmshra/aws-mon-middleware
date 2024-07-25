from django.db import models
from django.contrib.auth.models import User

class IAMUser(models.Model):
    user_id = models.CharField(max_length=255, unique=True)
    user_name = models.CharField(max_length=255)
    tags = models.JSONField(default=list, blank=True)
    last_login = models.TextField()

    class Meta:
        verbose_name = 'IAM User'
        verbose_name_plural = 'IAM Users'

class S3Bucket(models.Model):
    bucket_name = models.CharField(max_length=255, unique=True)
    creation_date = models.DateTimeField()
    tags = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'S3 Bucket'
        verbose_name_plural = 'S3 Buckets'

class EC2Instance(models.Model):
    instance_id = models.CharField(max_length=255, unique=True)
    instance_type = models.CharField(max_length=50)
    launch_time = models.DateTimeField()
    region = models.CharField(max_length=50)
    age = models.IntegerField()
    tags = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=50)
    potential_cost_savings = models.FloatField()
    recommendations = models.TextField()

    class Meta:
        verbose_name = 'EC2 Instance'
        verbose_name_plural = 'EC2 Instances'

class EBSVolume(models.Model):
    volume_id = models.CharField(max_length=255, unique=True)
    size = models.IntegerField()
    region = models.CharField(max_length=50)
    status = models.CharField(max_length=50, null=True)
    tags = models.JSONField(default=list, blank=True)
    potential_cost_savings = models.FloatField()
    recommendations = models.TextField()

    class Meta:
        verbose_name = 'EBS Volume'
        verbose_name_plural = 'EBS Volumes'

class RDSSnapshot(models.Model):
    snapshot_id = models.CharField(max_length=255, unique=True)
    creation_date = models.DateTimeField()
    tags = models.JSONField(default=list, blank=True)
    region = models.CharField(max_length=50)
    potential_cost_savings = models.FloatField()
    recommendations = models.TextField()

    class Meta:
        verbose_name = 'RDS Snapshot'
        verbose_name_plural = 'RDS Snapshots'

class ElasticIP(models.Model):
    allocation_id = models.CharField(max_length=255, unique=True)
    public_ip = models.GenericIPAddressField()
    region = models.CharField(max_length=50)
    tags = models.JSONField(default=list, blank=True)
    potential_cost_savings = models.FloatField()
    recommendations = models.TextField()
    age = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'Elastic IP'
        verbose_name_plural = 'Elastic IPs'

class RDSInstance(models.Model):
    db_instance_identifier = models.CharField(max_length=255, unique=True)
    db_instance_class = models.CharField(max_length=50)
    backup_type = models.CharField(max_length=50)
    tags = models.JSONField(default=list, blank=True)
    region = models.CharField(max_length=50)
    potential_cost_savings = models.FloatField()
    recommendations = models.TextField()

    class Meta:
        verbose_name = 'RDS Instance'
        verbose_name_plural = 'RDS Instances'

class EC2Snapshot(models.Model):
    snapshot_id = models.CharField(max_length=255, unique=True)
    creation_date = models.DateTimeField()
    tags = models.JSONField(default=list, blank=True)
    region = models.CharField(max_length=50)
    potential_cost_savings = models.FloatField()
    recommendations = models.TextField()

    class Meta:
        verbose_name = 'EC2 Snapshot'
        verbose_name_plural = 'EC2 Snapshots'

class Region(models.Model):
    name = models.CharField(max_length=50, unique=True)
    stopped_ec2_instances = models.ManyToManyField(EC2Instance, related_name='regions_stopped')
    unused_rds_instances = models.ManyToManyField(RDSInstance, related_name='regions_unused_rds')
    available_ebs_volumes = models.ManyToManyField(EBSVolume, related_name='regions_available_ebs')
    old_rds_snapshots = models.ManyToManyField(RDSSnapshot, related_name='regions_old_rds_snapshots')
    old_ec2_snapshots = models.ManyToManyField(EC2Snapshot, related_name='regions_old_ec2_snapshots')
    unused_elastic_ips = models.ManyToManyField(ElasticIP, related_name='regions_unused_elastic_ips')

    class Meta:
        verbose_name = 'Region'
        verbose_name_plural = 'Regions'


class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project_name = models.CharField(max_length=255)
    account_id = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.project_name} - {self.account_id}'
