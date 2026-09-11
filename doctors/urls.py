from django.urls import path
from . import views
app_name = 'doctors'
urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('cases/', views.case_list, name='case_list'),
    path('case/<uuid:case_id>/', views.case_detail, name='case_detail'),
    path('case/<uuid:case_id>/request-test/', views.request_test, name='request_test'),
    path('report/<int:report_id>/verify/', views.verify_report, name='verify_report'),
    path('case/<uuid:case_id>/ai-analysis/', views.run_ai_analysis, name='run_ai_analysis'),
    path('case/<uuid:case_id>/decision/', views.submit_decision, name='submit_decision'),
]
