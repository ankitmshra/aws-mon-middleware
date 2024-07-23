from django.urls import path
from .views import UpdateDataView

app_name = 'rmon'

urlpatterns = [
    path('update/', UpdateDataView.as_view(), name='update-data'),
]