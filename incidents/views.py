import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import IncidentForm, StatusUpdateForm
from .models import Incident, StatusUpdate

from django.db.models import Case, IntegerField, Q, When
@login_required
def report_view(request):
    if request.user.is_admin_user():
        messages.info(request, 'Admins cannot submit incidents.')
        return redirect('admin_panel')
    if request.method == 'POST':
        form = IncidentForm(request.POST, request.FILES)
        if form.is_valid():
            incident = form.save(commit=False)
            incident.reported_by = request.user
            incident.save()
            initial_status = incident.status
            if initial_status == 'ASSIGNED' and incident.assigned_to:
                dept_name = incident.department.name if incident.department else 'department queue'
                note = (
                    f'Incident reported by citizen. '
                    f'Auto-routed to {dept_name} and assigned to {incident.assigned_to.username} '
                    f'due to emergency priority.'
                )
            elif initial_status == 'ASSIGNED':
                note = 'Incident reported by citizen. Auto-routed due to emergency priority.'
            else:
                note = 'Incident reported by citizen.'

            StatusUpdate.objects.create(
                incident=incident,
                status=initial_status,
                note=note,
                updated_by=request.user,
            )
            messages.success(request, f'Incident {incident.tracking_id} submitted successfully!')
            return redirect('incident_detail', pk=incident.pk)
    else:
        form = IncidentForm()
    return render(request, 'incidents/report.html', {'form': form})


def incident_detail_view(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    status_form = None
    can_update = request.user.is_authenticated and (
        request.user.is_admin_user() or request.user.is_worker()
    )
    if can_update:
        status_form = StatusUpdateForm()

    if request.method == 'POST' and can_update:
        status_form = StatusUpdateForm(request.POST)
        if status_form.is_valid():
            new_status = status_form.cleaned_data['status']
            note = status_form.cleaned_data.get('note', '')
            incident.status = new_status
            if new_status == 'RESOLVED':
                incident.resolved_at = timezone.now()
            incident.save()
            StatusUpdate.objects.create(
                incident=incident,
                status=new_status,
                note=note,
                updated_by=request.user,
            )
            messages.success(request, 'Status updated.')
            return redirect('incident_detail', pk=pk)

    return render(request, 'incidents/detail.html', {
        'incident': incident,
        'status_form': status_form,
    })


@login_required
def my_incidents_view(request):
    if request.user.is_admin_user():
        messages.info(request, 'Admins do not have a personal reports list.')
        return redirect('admin_panel')
    incidents = Incident.objects.filter(reported_by=request.user).select_related('department')
    return render(request, 'incidents/my_incidents.html', {'incidents': incidents})


def incidents_api(request):
    priority_rank = Case(
    When(priority='EMERGENCY', then=0),
    When(priority='HIGH', then=1),
    When(priority='MEDIUM', then=2),
    When(priority='LOW', then=3),
    default=4,
    output_field=IntegerField(),
    )

    qs = (
        Incident.objects
        .select_related('department', 'reported_by')
        .annotate(priority_rank=priority_rank)
        .order_by('priority_rank', 'deadline', '-created_at')
    )

    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    area_filter = request.GET.get('area')
    q = request.GET.get('q')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if type_filter:
        qs = qs.filter(incident_type=type_filter)
    if area_filter:
        qs = qs.filter(area__icontains=area_filter)
    if q:
        qs = qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(tracking_id__icontains=q)
        )

    data = [
        {
            'id': inc.id,
            'tracking_id': inc.tracking_id,
            'title': inc.title,
            'incident_type': inc.incident_type,
            'incident_type_display': inc.get_incident_type_display(),
            'status': inc.status,
            'status_display': inc.get_status_display(),
            'priority': inc.priority,
            'priority_display': inc.get_priority_display(),
            'latitude': float(inc.latitude),
            'longitude': float(inc.longitude),
            'address': inc.address,
            'area': inc.area,
            'department': inc.department.name if inc.department else '',
            'reported_by': inc.reported_by.username,
            'created_at': inc.created_at.isoformat(),
            'image_url': inc.image.url if inc.image else None,
        }
        for inc in qs
    ]
    return JsonResponse({'incidents': data})


@login_required
@require_POST
def update_status_api(request, pk):
    if not (request.user.is_admin_user() or request.user.is_worker()):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    incident = get_object_or_404(Incident, pk=pk)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    new_status = body.get('status')
    note = body.get('note', '')
    assigned_to_id = body.get('assigned_to')
    department_id = body.get('department_id')

    valid_statuses = [s[0] for s in Incident.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    incident.status = new_status
    if new_status == 'RESOLVED':
        incident.resolved_at = timezone.now()

    # Allow admin to manually route MISC (or any unrouted) incident to a department
    if department_id:
        from .models import Department
        try:
            incident.department = Department.objects.get(pk=department_id)
        except Department.DoesNotExist:
            pass

    if assigned_to_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            incident.assigned_to = User.objects.get(pk=assigned_to_id)
            if incident.status == 'SUBMITTED':
                incident.status = 'ASSIGNED'
                new_status = 'ASSIGNED'
        except User.DoesNotExist:
            pass
    incident.save()
    StatusUpdate.objects.create(
        incident=incident, status=new_status, note=note, updated_by=request.user,
    )
    return JsonResponse({'success': True, 'status': new_status})
