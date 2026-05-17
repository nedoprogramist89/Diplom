"""Сигналы хакатонов: уведомлять зарегистрированных при смене этапа."""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Hackathon, HackathonRegistration


@receiver(pre_save, sender=Hackathon)
def hackathon_store_old_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_status = None
        return
    old = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
    instance._old_status = old


@receiver(post_save, sender=Hackathon)
def hackathon_notify_status_changed(sender, instance, created, **kwargs):
    if created:
        return
    old_status = getattr(instance, '_old_status', None)
    if not old_status or old_status == instance.status:
        return
    user_ids = (
        HackathonRegistration.objects.filter(hackathon_id=instance.pk)
        .values_list('user_id', flat=True)
        .distinct()
    )
    from accounts.notifications import bulk_notify

    bulk_notify(
        user_ids,
        kind='system',
        title=f'Хакатон «{instance.title}»: этап изменён',
        body=f'Новый этап: {instance.get_status_display()}.',
        link=f'/hackathons/{instance.pk}/',
    )
