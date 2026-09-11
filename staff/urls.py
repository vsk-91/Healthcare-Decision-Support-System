from django.urls import path
from . import views
app_name = 'staff'
urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('test-requests/', views.test_requests, name='test_requests'),
    path('test-request/<int:request_id>/', views.test_request_detail, name='test_request_detail'),
    path('test-request/<int:request_id>/upload/', views.upload_report, name='upload_report'),
    path('my-reports/', views.my_reports, name='my_reports'),
]
