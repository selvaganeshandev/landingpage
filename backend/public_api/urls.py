from django.urls import path

from . import views

urlpatterns = [
    path('workspaces', views.workspaces, name='v1_workspaces'),
    path('workspaces/', views.workspaces),
    path('me', views.me, name='v1_me'),
    path('me/', views.me),
]
