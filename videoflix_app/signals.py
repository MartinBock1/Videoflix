import os
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from .tasks import convert_480p

from .models import Video


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    print("Video wurde gespeichert")

    if created:
        print('new video created')
        convert_480p(instance.video_file.path)


@receiver(post_delete, sender=Video)
def video_post_delete(sender, instance, **kwargs):
    if instance.video_file:
        if os.path.isfile(instance.video_file.path):
            os.remove(instance.video_file.path)


post_save.connect(video_post_save, sender=Video)
