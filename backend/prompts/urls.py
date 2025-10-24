from django.urls import path
from . import views

urlpatterns = [
    # Mentions endpoints
    path('mentions/', views.get_mentions, name='get_mentions'),
    path('mentions/filters/', views.get_mention_filters, name='get_mention_filters'),
    path('mentions/<int:analytics_id>/', views.get_mention_detail, name='get_mention_detail'),
]