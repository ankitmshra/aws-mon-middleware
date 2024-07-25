import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, BotoCoreError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import AWSAccountCredentials
from .serializers import AWSAccountCredentialsSerializer

class SaveAWSCredentialsView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        serializer = AWSAccountCredentialsSerializer(data=request.data)
        if serializer.is_valid():
            # Extract credentials from validated data
            aws_access_key_id = serializer.validated_data['aws_access_key_id']
            aws_secret_access_key = serializer.validated_data['aws_secret_access_key']
            aws_region = serializer.validated_data['aws_region']
            
            # Attempt to create an S3 client to validate credentials
            try:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=aws_region
                )
                # Attempt to list S3 buckets to verify credentials
                s3_client.list_buckets()
                
                # Check if credentials already exist for the user
                aws_credentials, created = AWSAccountCredentials.objects.get_or_create(user=request.user)
                
                if not created:
                    # If the credentials already exist, update them
                    serializer.update(aws_credentials, serializer.validated_data)
                else:
                    # If credentials were newly created, save them
                    serializer.save(user=request.user)

                return Response({"message": "AWS credentials saved successfully."}, status=201)
            except (NoCredentialsError, PartialCredentialsError, BotoCoreError) as e:
                return Response({"error": "Invalid AWS credentials: " + str(e)}, status=400)
        return Response(serializer.errors, status=400)