from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
import os, django_rq, glob, shutil 

from .tasks import generate_thumbnail, convert_video_to_hls
from .models import Video


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    if created:
        queue = django_rq.get_queue('default')

        print(f"Neues Video '{instance.title}': Vorschaubild-Erstellung wird eingereiht.")
        queue.enqueue('videoflix_app.tasks.generate_thumbnail', instance.pk)

        print(f"Neues Video '{instance.title}': HLS-Konvertierung wird eingereiht.")
        queue.enqueue('videoflix_app.tasks.convert_video_to_hls', instance.pk)


@receiver(post_delete, sender=Video)
def video_post_delete(sender, instance, **kwargs):
    print(f"Lösche alle zugehörigen Dateien für: {instance.title}")
    
    if instance.thumbnail_url and hasattr(instance.thumbnail_url, 'path'):
        if os.path.isfile(instance.thumbnail_url.path):
            try:
                os.remove(instance.thumbnail_url.path)
                print(f"  -> Gelöscht: {instance.thumbnail_url.path}")
            except OSError as e:
                print(f"  -> Fehler beim Löschen von {instance.thumbnail_url.path}: {e}")

    if instance.video_file and hasattr(instance.video_file, 'path'):
        original_path = instance.video_file.path
        if os.path.isfile(original_path):
            try:
                os.remove(original_path)
                print(f"  -> Gelöscht (Original): {original_path}")
            except OSError as e:
                print(f"  -> Fehler beim Löschen von {original_path}: {e}")

        base_filename = os.path.splitext(os.path.basename(original_path))[0]
        video_dir = os.path.dirname(original_path)
        main_video_dir_to_delete = os.path.join(video_dir, base_filename)

        if os.path.isdir(main_video_dir_to_delete):
            try:
                shutil.rmtree(main_video_dir_to_delete)
                print(f"  -> Verzeichnis gelöscht: {main_video_dir_to_delete}")
            except OSError as e:
                print(f"  -> Fehler beim Löschen von {main_video_dir_to_delete}: {e}")
