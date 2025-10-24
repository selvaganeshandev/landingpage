from django.urls import path
from . import views

urlpatterns = [
    path('', views.keyword_list, name='keyword_list'),
    path('<int:pk>/', views.keyword_detail, name='keyword_detail'),
]
