from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
import os, django_rq, glob

from .tasks import convert_video_to_multiple_resolutions
from .models import Video


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    if created:
        print(f"Neues Video '{instance.title}' wird für die Konvertierung eingereiht.")
        queue = django_rq.get_queue('default')
        queue.enqueue(convert_video_to_multiple_resolutions, instance.pk)

@receiver(post_delete, sender=Video)
def video_post_delete(sender, instance, **kwargs):
    if instance.video_file and hasattr(instance.video_file, 'path'):
        root, ext = os.path.splitext(instance.video_file.path)        
        search_pattern = f"{root}_*{ext}"
        generated_files = glob.glob(search_pattern)
        all_files_to_delete = generated_files + [instance.video_file.path]
        
        print(f"Lösche alle Videodateien für: {instance.title}")
        for file_path in all_files_to_delete:
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"  -> Gelöscht: {file_path}")
                except OSError as e:
                    print(f"  -> Fehler beim Löschen von {file_path}: {e}")
