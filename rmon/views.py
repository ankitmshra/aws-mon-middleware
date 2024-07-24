import os

from django.conf import settings
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import filters
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.core.files.storage import FileSystemStorage

from .helpers.fetch_json import fetch_json as fj

class UpdateDataView(APIView):
    def get(self, request, *args, **kwargs):
        (data, fetch_status) = fj(settings.AWS_ACCESS_KEY, settings.AWS_SECRET_ACCESS_KEY, 
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

            return Response({"message": "Data saved successfully."}, status=200)
        
        else:
            return Response({"data": data}, status=status.HTTP_401_UNAUTHORIZED)