from django.urls import path

from . import views

urlpatterns = [
    path('report/', views.report_view, name='report_incident'),
    path('incidents/<int:pk>/', views.incident_detail_view, name='incident_detail'),
    path('my-incidents/', views.my_incidents_view, name='my_incidents'),
    path('api/incidents/', views.incidents_api, name='incidents_api'),
    path('api/incidents/<int:pk>/status/', views.update_status_api, name='update_status_api'),
]
