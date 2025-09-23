import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Consultation

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Consultation)
def consultation_created_signal(sender, instance, created, **kwargs):
    """
    Send WebSocket notification when a new consultation is created
    """
    logger.info(f"🔔 consultation_created_signal triggered: created={created}, status={instance.status}, id={instance.id}")
    channel_layer = get_channel_layer()

    if not channel_layer:
        logger.warning("No channel layer configured - WebSocket notifications disabled")
        return

    try:
        if created and instance.status == 'pending':
            # Send notification to all doctors for new pending consultations
            logger.info(f"Sending WebSocket notification for new consultation: {instance.id}")

            consultation_data = {
                'id': instance.id,
                'meeting_id': instance.meeting_id,
                'patient_name': f"{instance.patient.first_name} {instance.patient.last_name}".strip(),
                'patient_email': instance.patient.email,
                'symptoms': getattr(instance.ai_recommendation, 'symptoms', '') if instance.ai_recommendation else '',
                'status': instance.status,
                'is_urgent': instance.is_urgent,
                'created_at': instance.created_at.isoformat(),
                'scheduled_at': instance.scheduled_at.isoformat() if instance.scheduled_at else None,
            }

            async_to_sync(channel_layer.group_send)(
                "doctors",  # Send to all doctors
                {
                    'type': 'consultation_created',
                    'consultation': consultation_data,
                    'timestamp': instance.created_at.isoformat()
                }
            )
            logger.info(f"WebSocket notification sent for consultation {instance.id}")

        elif not created:
            # Send notification for consultation updates (status changes, etc.)
            logger.info(f"Sending WebSocket update for consultation: {instance.id}")

            consultation_data = {
                'id': instance.id,
                'meeting_id': instance.meeting_id,
                'patient_name': f"{instance.patient.first_name} {instance.patient.last_name}".strip(),
                'patient_email': instance.patient.email,
                'symptoms': getattr(instance.ai_recommendation, 'symptoms', '') if instance.ai_recommendation else '',
                'status': instance.status,
                'is_urgent': instance.is_urgent,
                'created_at': instance.created_at.isoformat(),
                'scheduled_at': instance.scheduled_at.isoformat() if instance.scheduled_at else None,
                'started_at': instance.started_at.isoformat() if instance.started_at else None,
                'ended_at': instance.ended_at.isoformat() if instance.ended_at else None,
            }

            async_to_sync(channel_layer.group_send)(
                "doctors",  # Send to all doctors
                {
                    'type': 'consultation_updated',
                    'consultation': consultation_data,
                    'timestamp': instance.updated_at.isoformat() if hasattr(instance, 'updated_at') else instance.created_at.isoformat()
                }
            )
            logger.info(f"WebSocket update sent for consultation {instance.id}")

    except Exception as e:
        logger.error(f"Error sending WebSocket notification for consultation {instance.id}: {str(e)}")


@receiver(pre_save, sender=Consultation)
def consultation_status_change_signal(sender, instance, **kwargs):
    """
    Detect status changes and send WebSocket notifications
    """
    if not instance.pk:
        # This is a new instance, not an update
        return

    try:
        # Get the previous instance from database
        previous_instance = Consultation.objects.get(pk=instance.pk)

        # Check if status has changed
        if previous_instance.status != instance.status:
            channel_layer = get_channel_layer()

            if not channel_layer:
                return

            logger.info(f"Status changed for consultation {instance.id}: {previous_instance.status} -> {instance.status}")

            consultation_data = {
                'id': instance.id,
                'meeting_id': instance.meeting_id,
                'patient_name': f"{instance.patient.first_name} {instance.patient.last_name}".strip(),
                'patient_email': instance.patient.email,
                'old_status': previous_instance.status,
                'new_status': instance.status,
                'is_urgent': instance.is_urgent,
                'created_at': instance.created_at.isoformat(),
                'scheduled_at': instance.scheduled_at.isoformat() if instance.scheduled_at else None,
            }

            # Send to all doctors
            async_to_sync(channel_layer.group_send)(
                "doctors",
                {
                    'type': 'consultation_status_changed',
                    'consultation': consultation_data,
                    'timestamp': instance.created_at.isoformat()
                }
            )

            # ✅ Also send to the specific patient
            async_to_sync(channel_layer.group_send)(
                f"user_{instance.patient.id}",
                {
                    'type': 'consultation_status_changed',
                    'consultation': consultation_data,
                    'timestamp': instance.created_at.isoformat()
                }
            )

            logger.info(f"WebSocket status change notification sent to doctors and patient {instance.patient.email} for consultation {instance.id}")

    except Consultation.DoesNotExist:
        # Instance doesn't exist yet, skip
        pass
    except Exception as e:
        logger.error(f"Error sending status change WebSocket notification for consultation {instance.id}: {str(e)}")