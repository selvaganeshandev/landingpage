from django.urls import path
from . import views

app_name = 'content'

urlpatterns = [
    path('generate/', views.generate_content, name='generate_content'),
    path('', views.get_generated_contents, name='get_generated_contents'),
    path('<int:content_id>/', views.get_generated_content, name='get_generated_content'),
    path('<int:content_id>/update/', views.update_generated_content, name='update_generated_content'),
    path('<int:content_id>/delete/', views.delete_generated_content, name='delete_generated_content'),
]


