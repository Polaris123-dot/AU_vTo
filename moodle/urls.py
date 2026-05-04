from django.urls import path
from . import views

app_name = 'moodle'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('curso/<int:tarea_id>/', views.course_detail, name='course_detail'),
    path('curso/<int:tarea_id>/ejecutar/', views.run_bot_view, name='run_bot'),
]
