from django.urls import path
from . import views

urlpatterns = [
    path('', views.keyword_list, name='keyword_list'),
    path('bulk-create/', views.bulk_create_keywords, name='bulk_create_keywords'),
    path('secondary/bulk-create/', views.bulk_create_secondary_keywords, name='bulk_create_secondary_keywords'),
    path('<int:pk>/', views.keyword_detail, name='keyword_detail'),
]
