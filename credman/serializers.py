from rest_framework import serializers
from .models import AWSAccountCredentials

class AWSAccountCredentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AWSAccountCredentials
        fields = ['aws_access_key_id', 'aws_secret_access_key', 'aws_region', 'bucket_name', 'object_key']

    def update(self, instance, validated_data):
        instance.aws_access_key_id = validated_data.get('aws_access_key_id', instance.aws_access_key_id)
        instance.aws_secret_access_key = validated_data.get('aws_secret_access_key', instance.aws_secret_access_key)
        instance.aws_region = validated_data.get('aws_region', instance.aws_region)
        instance.bucket_name = validated_data.get('bucket_name', instance.bucket_name)
        instance.object_key = validated_data.get('object_key', instance.object_key)
        instance.save()
        return instance