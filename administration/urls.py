from django.urls import path
from . import views

app_name = 'administration'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # User management
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/create-doctor/', views.create_doctor, name='create_doctor'),
    path('users/create-staff/', views.create_staff, name='create_staff'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/toggle/', views.user_toggle, name='user_toggle'),
    path('users/<int:user_id>/reset-password/', views.user_reset_password, name='user_reset_password'),

    # Datasets
    path('datasets/', views.dataset_list, name='dataset_list'),
    path('datasets/upload/', views.dataset_upload, name='dataset_upload'),
    path('datasets/<int:dataset_id>/delete/', views.dataset_delete, name='dataset_delete'),

    # AI Models
    path('models/', views.ai_model_list, name='ai_model_list'),
    path('models/create/', views.ai_model_create, name='ai_model_create'),
    path('models/<int:model_id>/train/', views.ai_model_train, name='ai_model_train'),

    # Audit logs
    path('audit/', views.audit_log_list, name='audit_log_list'),

    # Cases
    path('cases/', views.case_list, name='case_list'),
]
