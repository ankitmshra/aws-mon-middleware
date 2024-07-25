from django.urls import path
from .views import SaveAWSCredentialsView

app_name = 'credman'

urlpatterns = [
    path('save-aws-credentials/', 
    SaveAWSCredentialsView.as_view(), 
    name='save_aws_credentials'),
]