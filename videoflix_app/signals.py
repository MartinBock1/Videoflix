from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
import os, django_rq, glob

from .tasks import generate_thumbnail, convert_video_to_multiple_resolutions
from .models import Video


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    """
    Stellt nach dem Erstellen eines neuen Videos zwei Aufgaben in die Warteschlange:
    1. Schnelle Erstellung des Vorschaubildes.
    2. Langsame Konvertierung des Videos in verschiedene Auflösungen.
    
    Beide Funktionspfade werden als String übergeben, um Import-Fehler im Worker zu vermeiden.
    """
    if created:
        queue = django_rq.get_queue('default')
        
        # KORREKTER AUFRUF 1: Thumbnail-Erstellung
        print(f"Neues Video '{instance.title}': Vorschaubild-Erstellung wird eingereiht.")
        queue.enqueue('videoflix_app.tasks.generate_thumbnail', instance.pk)

        # KORREKTER AUFRUF 2: Video-Konvertierung
        print(f"Neues Video '{instance.title}': Video-Konvertierung wird eingereiht.")
        queue.enqueue('videoflix_app.tasks.convert_video_to_multiple_resolutions', instance.pk)


@receiver(post_delete, sender=Video)
def video_post_delete(sender, instance, **kwargs):
    files_to_delete = []

    # Das generierte Thumbnail zur Löschliste hinzufügen
    if instance.thumbnail_url and hasattr(instance.thumbnail_url, 'path'):
        if os.path.isfile(instance.thumbnail_url.path):
            files_to_delete.append(instance.thumbnail_url.path)
            
    # Original-Video und konvertierte Versionen zur Löschliste hinzufügen
    if instance.video_file and hasattr(instance.video_file, 'path'):
        # Pfad zum Originalvideo
        original_video_path = instance.video_file.path
        if os.path.isfile(original_video_path):
            files_to_delete.append(original_video_path)
        
        # Pfade zu den konvertierten Videos
        root, ext = os.path.splitext(original_video_path)        
        search_pattern = f"{root}_*{ext}"
        generated_files = glob.glob(search_pattern)
        files_to_delete.extend(generated_files)
    
    if files_to_delete:
        print(f"Lösche alle zugehörigen Dateien für: {instance.title}")
        for file_path in set(files_to_delete): # set() verwenden, um Duplikate zu vermeiden
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"  -> Gelöscht: {file_path}")
                except OSError as e:
                    print(f"  -> Fehler beim Löschen von {file_path}: {e}")