import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, BotoCoreError, ClientError
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
                
                # Remove any existing credentials for the user
                AWSAccountCredentials.objects.filter(user=request.user).delete()
                
                # Save the new credentials
                serializer.save(user=request.user)

                return Response({"message": "AWS credentials saved successfully."}, status=201)
            except NoCredentialsError:
                return Response({"error": "No AWS credentials found."}, status=400)
            except PartialCredentialsError:
                return Response({"error": "Partial AWS credentials provided."}, status=400)
            except ClientError as e:
                # Handle specific client errors, such as permissions issues
                return Response({"error": f"AWS Client error: {e.response['Error']['Message']}"}, status=400)
            except BotoCoreError as e:
                # Handle general boto3 core errors
                return Response({"error": f"BotoCore error: {str(e)}"}, status=400)
            except Exception as e:
                # Catch any other exceptions
                return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=500)
        return Response(serializer.errors, status=400)