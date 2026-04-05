import json

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import redirect, render
from django.utils import timezone
from datetime import timedelta
from django.db.models import Case, Count, IntegerField, When
from incidents.models import Department, Incident


def public_dashboard(request):
    total = Incident.objects.count()
    resolved = Incident.objects.filter(status='RESOLVED').count()
    pending = Incident.objects.exclude(status='RESOLVED').count()
    return render(request, 'dashboard/public.html', {
        'total': total,
        'resolved': resolved,
        'pending': pending,
        'type_choices': Incident.TYPE_CHOICES,
        'status_choices': Incident.STATUS_CHOICES,
    })


@login_required
def admin_panel(request):
    if not request.user.is_admin_user():
        return redirect('public_dashboard')

    priority_rank = Case(
    When(priority='EMERGENCY', then=0),
    When(priority='HIGH', then=1),
    When(priority='MEDIUM', then=2),
    When(priority='LOW', then=3),
    default=4,
    output_field=IntegerField(),
    )

    incidents = (
        Incident.objects
        .select_related('department', 'reported_by', 'assigned_to')
        .annotate(priority_rank=priority_rank)
        .order_by('priority_rank', 'deadline', '-created_at')
    )

    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    area_filter = request.GET.get('area', '').strip()
    if status_filter:
        incidents = incidents.filter(status=status_filter)
    if type_filter:
        incidents = incidents.filter(incident_type=type_filter)
    if area_filter:
        incidents = incidents.filter(area__icontains=area_filter)

    departments = Department.objects.all().order_by('name')
    unrouted_count = Incident.objects.filter(incident_type='MISC', department__isnull=True).count()

    return render(request, 'dashboard/admin_panel.html', {
        'incidents': incidents,
        'departments': departments,
        'unrouted_count': unrouted_count,
        'status_choices': Incident.STATUS_CHOICES,
        'type_choices': Incident.TYPE_CHOICES,
        'selected_status': status_filter,
        'selected_type': type_filter,
        'selected_area': area_filter,
    })


@login_required
def worker_panel(request):
    if not request.user.is_worker():
        return redirect('public_dashboard')
    priority_rank = Case(
    When(priority='EMERGENCY', then=0),
    When(priority='HIGH', then=1),
    When(priority='MEDIUM', then=2),
    When(priority='LOW', then=3),
    default=4,
    output_field=IntegerField(),
    )

    incidents = (
        Incident.objects
        .filter(assigned_to=request.user)
        .select_related('department')
        .annotate(priority_rank=priority_rank)
        .order_by('priority_rank', 'deadline', '-created_at')
    )
    return render(request, 'dashboard/worker_panel.html', {'incidents': incidents})


@login_required
def analytics_view(request):
    if request.user.role == 'citizen':
        return redirect('public_dashboard')

    by_type = list(Incident.objects.values('incident_type').annotate(count=Count('id')))
    type_labels = [d['incident_type'] for d in by_type]
    type_counts = [d['count'] for d in by_type]

    by_status = list(Incident.objects.values('status').annotate(count=Count('id')))
    status_labels = [d['status'] for d in by_status]
    status_counts = [d['count'] for d in by_status]

    thirty_days_ago = timezone.now() - timedelta(days=30)
    trend = list(
        Incident.objects
        .filter(created_at__gte=thirty_days_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    trend_labels = [str(d['day']) for d in trend]
    trend_counts = [d['count'] for d in trend]

    heatmap_data = list(Incident.objects.values_list('latitude', 'longitude'))
    heatmap_json = json.dumps([[float(lat), float(lng), 1] for lat, lng in heatmap_data])

    return render(request, 'dashboard/analytics.html', {
        'type_labels': json.dumps(type_labels),
        'type_counts': json.dumps(type_counts),
        'status_labels': json.dumps(status_labels),
        'status_counts': json.dumps(status_counts),
        'trend_labels': json.dumps(trend_labels),
        'trend_counts': json.dumps(trend_counts),
        'heatmap_json': heatmap_json,
        'total': Incident.objects.count(),
        'resolved': Incident.objects.filter(status='RESOLVED').count(),
        'escalated': Incident.objects.filter(status='ESCALATED').count(),
    })
