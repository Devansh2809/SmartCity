from django.urls import path

from . import views

urlpatterns = [
    path('', views.public_dashboard, name='public_dashboard'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('worker-panel/', views.worker_panel, name='worker_panel'),
    path('analytics/', views.analytics_view, name='analytics'),
]
