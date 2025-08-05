import subprocess
import shlex
import os
import shutil
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

    thumbnail_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
    os.makedirs(thumbnail_dir, exist_ok=True)

    filename = os.path.splitext(os.path.basename(source_path))[0]
    target_path = os.path.join(thumbnail_dir, f"{filename}.jpg")

    cmd_string = f'ffmpeg -i "{source_path}" -ss 00:00:01.000 -vframes 1 "{target_path}"'
    cmd_list = shlex.split(cmd_string)

    try:
        subprocess.run(cmd_list, check=True, capture_output=True, text=True)
        print(f"  -> Erfolgreich Vorschaubild erstellt: {target_path}")

        relative_path = os.path.relpath(target_path, settings.MEDIA_ROOT)
        video.thumbnail_url.name = relative_path
        video.save(update_fields=['thumbnail_url'])

    except FileNotFoundError:
        print("FEHLER im Worker: 'ffmpeg' wurde nicht gefunden.")
    except subprocess.CalledProcessError as e:
        print(f"  -> FEHLER bei der Erstellung des Vorschaubildes: {e.stderr.strip()}")


def convert_video_to_hls(video_id):
    try:
        video = Video.objects.get(pk=video_id)
        source_path = video.video_file.path
        base_filename = os.path.splitext(os.path.basename(source_path))[0]
        base_output_dir = os.path.dirname(source_path)
        main_video_dir = os.path.join(base_output_dir, base_filename)
        os.makedirs(main_video_dir, exist_ok=True)

        print(f"HLS-Konvertierung gestartet für Video ID {video_id}")
    except Video.DoesNotExist:
        print(f"FEHLER: Video mit ID {video_id} wurde nicht gefunden.")
        return

    resolutions = [('480p', '854x480'), ('720p', '1280x720'), ('1080p', '1920x1080')]
    temp_mp4_files = []

    print("-> Schritt 1: Erstelle temporäre MP4-Dateien...")
    for suffix, size in resolutions:
        target_mp4_path = os.path.join(main_video_dir, f"{base_filename}_{suffix}.mp4")
        temp_mp4_files.append(target_mp4_path)
        cmd_string = f'ffmpeg -i "{source_path}" -s {size} -c:v libx264 -crf 23 -c:a aac "{target_mp4_path}"'
        try:
            subprocess.run(shlex.split(cmd_string), check=True,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900)
            print(f"  - Erfolgreich erstellt: {target_mp4_path}")
        except Exception as e:
            print(f"  - FEHLER beim Erstellen von {target_mp4_path}: {e}")
            cleanup_files(temp_mp4_files)
            return

    print("-> Schritt 2: Konvertiere MP4-Dateien in HLS-Streams...")
    for mp4_file_path in temp_mp4_files:
        resolution_suffix = os.path.basename(mp4_file_path).replace(
            base_filename + '_', '').replace('.mp4', '')
        hls_output_dir = os.path.join(main_video_dir, resolution_suffix)
        os.makedirs(hls_output_dir, exist_ok=True)
        hls_playlist_path = os.path.join(hls_output_dir, 'index.m3u8')

        cmd_string = (
            f'ffmpeg -i "{mp4_file_path}" -c:v copy -c:a copy '
            f'-tag:v hvc1 -bsf:v h264_mp4toannexb '
            f'-hls_segment_filename "{hls_output_dir}/%03d.ts" '
            f'-start_number 0 -hls_time 10 -hls_list_size 0 -f hls "{hls_playlist_path}"'
        )
        try:
            subprocess.run(shlex.split(cmd_string), check=True,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
            print(f"  - Erfolgreich HLS für {resolution_suffix} erstellt.")
        except Exception as e:
            if isinstance(e, subprocess.CalledProcessError):
                print(
                    f"  -> FEHLER bei HLS-Konvertierung von {mp4_file_path}.\n  -> STDERR: {e.stderr.strip()}")
            else:
                print(f"  - FEHLER bei der HLS-Konvertierung von {mp4_file_path}: {e}")

    print("-> Schritt 3: Lösche temporäre MP4-Dateien und Original...")
    cleanup_files(temp_mp4_files)
    cleanup_files([source_path])


def cleanup_files(file_list):
    for file_path in file_list:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"  - Gelöscht: {file_path}")
        except OSError as e:
            print(f"  - Fehler beim Löschen von {file_path}: {e}")
