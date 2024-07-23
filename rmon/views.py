from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import filters
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

class UpdateDataView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            print("test update api")
            return Response({"message": "Data updated successfully."},
                            status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)