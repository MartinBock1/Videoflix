from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
import os
import django_rq
import glob
import shutil

from .models import Video


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    """
    Signal handler that runs after a Video instance is saved.

    If a new video is created, this function enqueues background tasks
    to generate its thumbnail and convert it to HLS format.

    Args:
        sender: The model class that sent the signal (Video).
        instance: The actual instance of the model being saved.
        created (bool): True if a new record was created.
        **kwargs: Wildcard keyword arguments.
    """
    # The 'created' flag ensures these tasks run only once when the video
    # is first uploaded, not every time the model is updated.
    if created:
        # Get the default RQ queue.
        queue = django_rq.get_queue('default')

        # Pass the primary key (pk) of the instance to the tasks instead of
        # the object itself. This is a best practice for background tasks.
        print(f"Neues Video '{instance.title}': Vorschaubild-Erstellung wird eingereiht.")
        queue.enqueue('videoflix_app.tasks.generate_thumbnail', instance.pk)

        print(f"Neues Video '{instance.title}': HLS-Konvertierung wird eingereiht.")
        queue.enqueue('videoflix_app.tasks.convert_video_to_hls', instance.pk)


@receiver(post_delete, sender=Video)
def video_post_delete(sender, instance, **kwargs):
    """
    Signal handler that runs after a Video instance is deleted.

    This function cleans up all associated files from the filesystem to
    prevent orphaned files. This includes the thumbnail, the original
    video file, and the entire directory of HLS stream files.

    Args:
        sender: The model class that sent the signal (Video).
        instance: The actual instance of the model being deleted.
        **kwargs: Wildcard keyword arguments.
    """
    print(f"Lösche alle zugehörigen Dateien für: {instance.title}")

    # --- 1. Delete the thumbnail file ---
    # Check if the thumbnail field has a file and a valid path.
    if instance.thumbnail_url and hasattr(instance.thumbnail_url, 'path'):
        if os.path.isfile(instance.thumbnail_url.path):
            try:
                os.remove(instance.thumbnail_url.path)
                print(f"  -> Gelöscht: {instance.thumbnail_url.path}")
            except OSError as e:
                print(f"  -> Fehler beim Löschen von {instance.thumbnail_url.path}: {e}")

    # --- 2. Delete the video files and HLS directory ---
    # Check if the video_file field has a file and a valid path.
    if instance.video_file and hasattr(instance.video_file, 'path'):
        original_path = instance.video_file.path

        # Delete the original uploaded video file.
        if os.path.isfile(original_path):
            try:
                os.remove(original_path)
                print(f"  -> Gelöscht (Original): {original_path}")
            except OSError as e:
                print(f"  -> Fehler beim Löschen von {original_path}: {e}")

        # Construct the path to the main directory containing HLS files.
        # e.g., 'media/videos/my_video_title/'
        base_filename = os.path.splitext(os.path.basename(original_path))[0]
        video_dir = os.path.dirname(original_path)
        main_video_dir_to_delete = os.path.join(video_dir, base_filename)

        # Recursively delete the HLS directory and all its contents.
        if os.path.isdir(main_video_dir_to_delete):
            try:
                shutil.rmtree(main_video_dir_to_delete)
                print(f"  -> Verzeichnis gelöscht: {main_video_dir_to_delete}")
            except OSError as e:
                print(f"  -> Fehler beim Löschen von {main_video_dir_to_delete}: {e}")
