from django.urls import path
from . import views

urlpatterns = [
    path('', views.domain_list, name='domain_list'),
    path('<int:pk>/', views.domain_detail, name='domain_detail'),
    path('<int:pk>/keywords/', views.domain_keywords, name='domain_keywords'),
    
    # Domain Access Management
    path('<int:domain_id>/access/', views.domain_access_list, name='domain_access_list'),
    path('<int:domain_id>/access/<int:user_id>/', views.domain_access_detail, name='domain_access_detail'),
    path('<int:domain_id>/access/available-users/', views.available_users_for_domain, name='available_users_for_domain'),
    
    # Detected Models
    path('detected-models/', views.detected_models_list, name='detected_models_list'),
    path('detected-models/<int:pk>/', views.detected_model_detail, name='detected_model_detail'),
]
