import subprocess, shlex, os
from django.conf import settings

from .models import Video

def generate_thumbnail(video_id):
    try:
        video = Video.objects.get(pk=video_id)
        if video.thumbnail_url and video.thumbnail_url.name:
            print(f"Vorschaubild für Video ID {video_id} existiert bereits.")
            return
    except Video.DoesNotExist:
        print(f"FEHLER: Video mit ID {video_id} für Thumbnail-Erstellung nicht gefunden.")
        return

    source_path = video.video_file.path
    
    # Zielpfad für das Thumbnail im 'thumbnails' Unterordner definieren
    thumbnail_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
    os.makedirs(thumbnail_dir, exist_ok=True) # Ordner erstellen, falls nicht vorhanden
    
    # Dateinamen ohne Erweiterung extrahieren und .jpg anhängen
    filename = os.path.splitext(os.path.basename(source_path))[0]
    target_path = os.path.join(thumbnail_dir, f"{filename}.jpg")

    # ffmpeg-Befehl: -ss springt zu Sekunde 1, -vframes 1 extrahiert genau einen Frame
    cmd_string = f'ffmpeg -i "{source_path}" -ss 00:00:01.000 -vframes 1 "{target_path}"'
    cmd_list = shlex.split(cmd_string)

    try:
        subprocess.run(cmd_list, check=True, capture_output=True, text=True)
        print(f"  -> Erfolgreich Vorschaubild erstellt: {target_path}")

        # Relativen Pfad zum Speichern im FileField des Modells erstellen
        relative_path = os.path.relpath(target_path, settings.MEDIA_ROOT)
        video.thumbnail_url.name = relative_path
        video.save(update_fields=['thumbnail_url']) # Nur das thumbnail_url Feld aktualisieren
        
    except FileNotFoundError:
        print("FEHLER im Worker: 'ffmpeg' wurde nicht gefunden.")
    except subprocess.CalledProcessError as e:
        print(f"  -> FEHLER bei der Erstellung des Vorschaubildes: {e.stderr.strip()}")
        

def convert_video_to_multiple_resolutions(video_id, crf_value=23):
    try:
        video = Video.objects.get(pk=video_id)
        source = video.video_file.path
        print(f"Task gestartet für Video ID {video_id}: {source}")
    except Video.DoesNotExist:
        print(f"FEHLER: Video mit ID {video_id} wurde nicht gefunden. Task wird beendet.")
        return

    resolutions = [
        ('480p', 'hd480'),
        ('720p', 'hd720'),
        ('1080p', 'hd1080')
    ]
    root, ext = os.path.splitext(source)

    for suffix, size_param in resolutions:
        target = f"{root}_{suffix}{ext}"
        cmd_string = f'ffmpeg -i "{source}" -s {size_param} -c:v libx264 -crf {crf_value} -c:a aac -strict -2 "{target}"'
        cmd_list = shlex.split(cmd_string)

        try:
            subprocess.run(cmd_list, check=True, capture_output=True, text=True)
            print(f"  -> Erfolgreich erstellt: {target}")
        except FileNotFoundError:
            print("FEHLER im Worker: 'ffmpeg' wurde nicht gefunden. Ist es im Docker-Image des Workers installiert?")
            return
        except subprocess.CalledProcessError as e:
            print(f"  -> FEHLER bei der Konvertierung zu {target}: {e.stderr.strip()}")
