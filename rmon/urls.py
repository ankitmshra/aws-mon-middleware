from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from .views import UpdateDataView, IAMUserListView, \
    S3BucketListView, RegionDetailView, \
    TotalResourceCountView, AllResourcesView, \
    FetchAccountDetailsView, LatestCumulativeCostView, \
        CumulativeCostRangeView


app_name = 'rmon'

urlpatterns = [
    path('update/', UpdateDataView.as_view(), name='update-data'),
    
    path('iam-users/', IAMUserListView.as_view(), name='iam-user-list'),

    path('s3-buckets/', S3BucketListView.as_view(), 
    name='s3-bucket-list'),

    path('regions/<str:name>/', RegionDetailView.as_view(), 
    name='region-detail'),

    path('resource-per-region/', TotalResourceCountView.as_view(), 
    name='total-resource-count'),

    path('all-resources/', AllResourcesView.as_view(), 
    name='all-resources'),

    path('account-details/', FetchAccountDetailsView.as_view(), 
    name='fetch_account_details'),

    path('latest-cumulative-cost/', 
    LatestCumulativeCostView.as_view(), 
    name='latest_cumulative_cost'),

    path('cumulative-cost-range/', 
    CumulativeCostRangeView.as_view(), 
    name='cumulative_cost_range'),
]