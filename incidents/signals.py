from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import StatusUpdate


@receiver(post_save, sender=StatusUpdate)
def broadcast_status_update(sender, instance, created, **kwargs):
    if not created:
        return
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    data = {
        'incident_id': instance.incident.pk,
        'tracking_id': instance.incident.tracking_id,
        'title': instance.incident.title,
        'status': instance.status,
        'status_display': instance.get_status_display(),
        'note': instance.note,
        'updated_by': instance.updated_by.username if instance.updated_by else 'System',
        'timestamp': instance.timestamp.isoformat(),
    }
    async_to_sync(channel_layer.group_send)(
        'incidents_live',
        {'type': 'incident.update', 'data': data},
    )
