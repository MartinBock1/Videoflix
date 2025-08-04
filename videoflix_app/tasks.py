import subprocess
import shlex
import os

from .models import Video


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
