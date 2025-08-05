import os
import tempfile
from unittest.mock import patch, call

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from ..models import Video

FAKE_VIDEO_CONTENT = b'GIF89a\x01\x00\x01\x00\x00\x00\x00\x00'
TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix='videoflix_test_media_')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class SignalsAndTasksTest(TestCase):

    def setUp(self):
        fake_video_file = SimpleUploadedFile(
            "test_video.mp4",
            FAKE_VIDEO_CONTENT,
            content_type="video/mp4"
        )
        self.video = Video.objects.create(
            title="Test Video",
            description="A test description",
            category="Testing",
            video_file=fake_video_file
        )

    def tearDown(self):
        for root, dirs, files in os.walk(TEMP_MEDIA_ROOT, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

    @patch('videoflix_app.signals.django_rq.get_queue')
    def test_post_save_signal_enqueues_correct_tasks(self, mock_get_queue):
        mock_queue = mock_get_queue.return_value
        new_video_file = SimpleUploadedFile("new.mp4", FAKE_VIDEO_CONTENT)
        new_video = Video.objects.create(
            title="New", description="d", category="c", video_file=new_video_file
        )
        expected_calls = [
            call('videoflix_app.tasks.generate_thumbnail', new_video.pk),
            call('videoflix_app.tasks.convert_video_to_multiple_resolutions', new_video.pk)
        ]
        mock_queue.enqueue.assert_has_calls(expected_calls, any_order=True)

    # KORREKTUR: Wir fügen einen Patch für os.path.isfile hinzu
    @patch('videoflix_app.signals.os.path.isfile', return_value=True)
    @patch('videoflix_app.signals.glob.glob')
    @patch('videoflix_app.signals.os.remove')
    def test_post_delete_signal_removes_files(self, mock_os_remove, mock_glob, mock_os_path_isfile):
        """
        Testet, ob das `post_delete`-Signal versucht, alle zugehörigen
        Dateien zu löschen.
        """
        original_path = self.video.video_file.path
        generated_files_paths = [
            f"{os.path.splitext(original_path)[0]}_480p.mp4",
            f"{os.path.splitext(original_path)[0]}_720p.mp4",
        ]
        mock_glob.return_value = generated_files_paths
        
        self.video.delete()

        # Überprüfen, ob isfile für alle potenziellen Dateien aufgerufen wurde
        self.assertTrue(mock_os_path_isfile.called)

        # Überprüfen, ob os.remove für alle Dateien aufgerufen wurde
        expected_files_to_remove = [
            call(original_path),
            call(generated_files_paths[0]),
            call(generated_files_paths[1]),
        ]
        mock_os_remove.assert_has_calls(expected_files_to_remove, any_order=True)

    @patch('subprocess.run')
    def test_generate_thumbnail_task(self, mock_subprocess_run):
        from ..tasks import generate_thumbnail
        generate_thumbnail(self.video.pk)
        self.assertTrue(mock_subprocess_run.called)
        self.video.refresh_from_db()
        self.assertIn('thumbnails/test_video.jpg', self.video.thumbnail_url.name)
        mock_subprocess_run.assert_called_once()

    @patch('subprocess.run')
    def test_convert_video_task(self, mock_subprocess_run):
        from ..tasks import convert_video_to_multiple_resolutions
        convert_video_to_multiple_resolutions(self.video.pk)
        self.assertEqual(mock_subprocess_run.call_count, 3)
