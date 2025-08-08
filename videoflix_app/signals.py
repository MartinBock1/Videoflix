import os, django_rq, shutil
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

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
    if created:
        queue = django_rq.get_queue('default')
        print(f"New video '{instance.title}': thumbnail creation is enqueued.")
        queue.enqueue('videoflix_app.tasks.generate_thumbnail', instance.pk)

        print(f"New video '{instance.title}': HLS conversion is enqueued.")
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
    print(f"Delete all related files for: {instance.title}")

    # --- 1. Delete the thumbnail file ---
    if instance.thumbnail_url and hasattr(instance.thumbnail_url, 'path'):
        if os.path.isfile(instance.thumbnail_url.path):
            try:
                os.remove(instance.thumbnail_url.path)
                print(f"  -> Deleted: {instance.thumbnail_url.path}")
            except OSError as e:
                print(f"  -> Error when deleting {instance.thumbnail_url.path}: {e}")

    # --- 2. Delete the video files and HLS directory ---
    if instance.video_file and hasattr(instance.video_file, 'path'):
        original_path = instance.video_file.path

        # Delete the original uploaded video file.
        if os.path.isfile(original_path):
            try:
                os.remove(original_path)
                print(f"  -> Deleted (original): {original_path}")
            except OSError as e:
                print(f"  -> Error when deleting {original_path}: {e}")

        # Construct the path to the main directory containing HLS files.
        base_filename = os.path.splitext(os.path.basename(original_path))[0]
        video_dir = os.path.dirname(original_path)
        main_video_dir_to_delete = os.path.join(video_dir, base_filename)

        # Recursively delete the HLS directory and all its contents.
        if os.path.isdir(main_video_dir_to_delete):
            try:
                shutil.rmtree(main_video_dir_to_delete)
                print(f"  -> Directory deleted: {main_video_dir_to_delete}")
            except OSError as e:
                print(f"  -> Error when deleting {main_video_dir_to_delete}: {e}")
