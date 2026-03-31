from django.contrib import admin

from .models import Department, Incident, StatusUpdate


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'email', 'phone']


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = [
        'tracking_id', 'title', 'incident_type', 'status',
        'priority', 'department', 'reported_by', 'created_at',
    ]
    list_filter = ['status', 'incident_type', 'priority', 'department']
    search_fields = ['tracking_id', 'title', 'area', 'reported_by__username']
    readonly_fields = ['tracking_id', 'created_at', 'updated_at']


@admin.register(StatusUpdate)
class StatusUpdateAdmin(admin.ModelAdmin):
    list_display = ['incident', 'status', 'updated_by', 'timestamp']
    list_filter = ['status']
