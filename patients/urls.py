from django.urls import path
from . import views
app_name = 'patients'
urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('new-case/', views.new_case, name='new_case'),
    path('my-cases/', views.my_cases, name='my_cases'),
    path('case/<uuid:case_id>/', views.case_detail, name='case_detail'),
    path('results/', views.results, name='results'),
]
