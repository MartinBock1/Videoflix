import subprocess
import shlex
import os

from django.conf import settings

from .models import Video


def generate_thumbnail(video_id):
    """
    Generates a thumbnail for a given video using ffmpeg.

    This function is intended to be run as a background task. It takes a
    single frame from the beginning of the video and saves it as a JPG.

    Args:
        video_id (int): The primary key of the Video object.
    """
    try:
        video = Video.objects.get(pk=video_id)
        # Optimization: If a thumbnail already exists, do nothing.
        if video.thumbnail_url and video.thumbnail_url.name:
            print(f"Thumbnail for Video ID {video_id} already exists.")
            return
    except Video.DoesNotExist:
        print(f"ERROR: Video with ID {video_id} not found for thumbnail generation.")
        return

    source_path = video.video_file.path

    # Ensure the target directory exists.
    thumbnail_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
    os.makedirs(thumbnail_dir, exist_ok=True)

    # Define the output path for the new thumbnail.
    filename = os.path.splitext(os.path.basename(source_path))[0]
    target_path = os.path.join(thumbnail_dir, f"{filename}.jpg")

    # Command to extract one frame (-vframes 1) from the 1-second mark (-ss).
    cmd_string = f'ffmpeg -i "{source_path}" -ss 00:00:01.000 -vframes 1 "{target_path}"'
    # Use shlex.split to safely parse the command string for subprocess.
    cmd_list = shlex.split(cmd_string)

    try:
        # Run the ffmpeg command. check=True raises an error on failure.
        subprocess.run(cmd_list, check=True, capture_output=True, text=True)
        print(f"  -> Successfully created thumbnail: {target_path}")

        # Save the relative path of the new thumbnail to the Video model.
        relative_path = os.path.relpath(target_path, settings.MEDIA_ROOT)
        video.thumbnail_url.name = relative_path
        # Use update_fields for an efficient database update.
        video.save(update_fields=['thumbnail_url'])

    except FileNotFoundError:
        print("ERROR in worker: 'ffmpeg' command not found. Is it installed?")
    except subprocess.CalledProcessError as e:
        print(f"  -> ERROR creating thumbnail: {e.stderr.strip()}")


def convert_video_to_hls(video_id):
    """
    Converts a video file to HLS format in multiple resolutions.

    This is a multi-step process:
    1. Re-encodes the original video into separate MP4 files for each resolution.
    2. Converts each MP4 file into an HLS stream (playlist and segments).
    3. Cleans up the temporary MP4 files and the original uploaded video.

    Args:
        video_id (int): The primary key of the Video object.
    """
    try:
        video = Video.objects.get(pk=video_id)
        source_path = video.video_file.path
        base_filename = os.path.splitext(os.path.basename(source_path))[0]
        base_output_dir = os.path.dirname(source_path)
        # The main output directory will be named after the video file.
        # e.g., /media/videos/my_awesome_video/
        main_video_dir = os.path.join(base_output_dir, base_filename)
        os.makedirs(main_video_dir, exist_ok=True)

        print(f"HLS conversion started for Video ID {video_id}")
    except Video.DoesNotExist:
        print(f"ERROR: Video with ID {video_id} not found for HLS conversion.")
        return

    # Define the target resolutions and their dimensions.
    resolutions = [('480p', '854x480'), ('720p', '1280x720'), ('1080p', '1920x1080')]
    temp_mp4_files = []

    # --- Step 1: Create temporary MP4 files for each resolution ---
    print("-> Step 1: Creating temporary MP4 files...")
    for suffix, size in resolutions:
        target_mp4_path = os.path.join(main_video_dir, f"{base_filename}_{suffix}.mp4")
        temp_mp4_files.append(target_mp4_path)
        # Command to resize (-s) and re-encode the video.
        cmd_string = (f'ffmpeg -i "{source_path}" -s {size} -c:v libx264 '
                      f'-crf 23 -c:a aac "{target_mp4_path}"')
        try:
            subprocess.run(shlex.split(cmd_string), check=True,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900)
            print(f"  - Successfully created: {target_mp4_path}")
        except Exception as e:
            print(f"  - ERROR creating {target_mp4_path}: {e}")
            cleanup_files(temp_mp4_files)
            return

    # --- Step 2: Convert each MP4 file into an HLS stream ---
    print("-> Step 2: Converting MP4 files to HLS streams...")
    for mp4_file_path in temp_mp4_files:
        resolution_suffix = os.path.basename(mp4_file_path).replace(
            base_filename + '_', '').replace('.mp4', '')
        # Create a subdirectory for each resolution's HLS files.
        hls_output_dir = os.path.join(main_video_dir, resolution_suffix)
        os.makedirs(hls_output_dir, exist_ok=True)
        hls_playlist_path = os.path.join(hls_output_dir, 'index.m3u8')

        # Command to segment the MP4 into .ts files and create an .m3u8 playlist.
        # '-c copy' is used for speed as no re-encoding is needed here.
        cmd_string = (
            f'ffmpeg -i "{mp4_file_path}" -c:v copy -c:a copy '
            f'-tag:v hvc1 -bsf:v h264_mp4toannexb '
            f'-hls_segment_filename "{hls_output_dir}/%03d.ts" '
            f'-start_number 0 -hls_time 10 -hls_list_size 0 -f hls "{hls_playlist_path}"'
        )
        try:
            subprocess.run(shlex.split(cmd_string), check=True,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
            print(f"  - Successfully created HLS for {resolution_suffix}.")
        except Exception as e:
            if isinstance(e, subprocess.CalledProcessError):
                print(f"  -> ERROR during HLS conversion of {mp4_file_path}.\n"
                      f"  -> STDERR: {e.stderr.strip()}")
            else:
                print(f"  - ERROR during HLS conversion of {mp4_file_path}: {e}")

    # --- Step 3: Clean up temporary files and the original video ---
    print("-> Step 3: Cleaning up temporary and original files...")
    cleanup_files(temp_mp4_files)
    # The original uploaded file is no longer needed.
    cleanup_files([source_path])


def cleanup_files(file_list):
    """
    A helper function to safely delete a list of files.
    """
    for file_path in file_list:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"  - Deleted: {file_path}")
        except OSError as e:
            print(f"  - Error deleting file {file_path}: {e}")
