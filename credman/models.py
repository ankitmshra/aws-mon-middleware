from django.db import models
from django.contrib.auth.models import User

class AWSAccountCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    aws_access_key_id = models.CharField(max_length=100)
    aws_secret_access_key = models.CharField(max_length=100)
    aws_region = models.CharField(max_length=50)
    bucket_name = models.CharField(max_length=100)
    object_key = models.CharField(max_length=100)

    def __str__(self):
        return f"AWS Credentials for {self.user.username}"