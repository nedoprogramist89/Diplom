"""Сигналы соревнований: уведомлять участников при смене этапа турнира."""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Competition, Participation


@receiver(pre_save, sender=Competition)
def competition_store_old_status(sender, instance, **kwargs):
    """Сохраняем старый статус перед сохранением для сравнения после save()."""
    if not instance.pk:
        instance._old_status = None
        return
    old = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
    instance._old_status = old


@receiver(post_save, sender=Competition)
def competition_notify_status_changed(sender, instance, created, **kwargs):
    """Уведомление всем участникам, если этап соревнования изменился."""
    if created:
        return
    old_status = getattr(instance, '_old_status', None)
    if not old_status or old_status == instance.status:
        return
    user_ids = (
        Participation.objects.filter(competition_id=instance.pk)
        .values_list('user_id', flat=True)
        .distinct()
    )
    from accounts.notifications import bulk_notify

    bulk_notify(
        user_ids,
        kind='system',
        title=f'Соревнование «{instance.title}»: этап изменён',
        body=f'Новый этап: {instance.get_status_display()}.',
        link=f'/competitions/{instance.pk}/',
    )
