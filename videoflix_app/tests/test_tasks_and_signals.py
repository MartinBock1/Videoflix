import os
import tempfile
from unittest.mock import patch, call

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from ..models import Video
from ..tasks import generate_thumbnail, convert_video_to_hls

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
                try:
                    os.remove(os.path.join(root, name))
                except OSError:
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass

    @patch('videoflix_app.signals.django_rq.get_queue')
    def test_post_save_signal_enqueues_correct_tasks(self, mock_get_queue):
        mock_queue = mock_get_queue.return_value
        new_video_file = SimpleUploadedFile("new.mp4", FAKE_VIDEO_CONTENT)
        new_video = Video.objects.create(
            title="New", description="d", category="c", video_file=new_video_file)

        expected_calls = [
            call('videoflix_app.tasks.generate_thumbnail', new_video.pk),
            call('videoflix_app.tasks.convert_video_to_hls', new_video.pk)
        ]
        mock_queue.enqueue.assert_has_calls(expected_calls, any_order=True)

    @patch('videoflix_app.signals.shutil.rmtree')
    @patch('videoflix_app.signals.os.remove')
    @patch('videoflix_app.signals.os.path.isfile', return_value=True)
    @patch('videoflix_app.signals.os.path.isdir', return_value=True)
    def test_post_delete_signal_removes_main_directory(self, mock_isdir, mock_isfile, mock_os_remove, mock_rmtree):
        original_path = self.video.video_file.path
        base_filename = os.path.splitext(os.path.basename(original_path))[0]
        video_dir = os.path.dirname(original_path)
        expected_dir_to_delete = os.path.join(video_dir, base_filename)
        self.video.delete()
        mock_os_remove.assert_called_with(original_path)
        mock_rmtree.assert_called_with(expected_dir_to_delete)

    @patch('subprocess.run')
    def test_generate_thumbnail_task(self, mock_subprocess_run):
        generate_thumbnail(self.video.pk)
        self.assertTrue(mock_subprocess_run.called)

    @patch('videoflix_app.tasks.os.remove')
    @patch('videoflix_app.tasks.os.path.exists', return_value=True)
    @patch('videoflix_app.tasks.subprocess.run')
    def test_convert_to_hls_task_logic(self, mock_subprocess_run, mock_exists, mock_remove):
        convert_video_to_hls(self.video.pk)
        self.assertEqual(mock_subprocess_run.call_count, 6)
        call_args_hls = mock_subprocess_run.call_args_list[3].args[0]
        command_str_hls = ' '.join(call_args_hls)
        self.assertIn('test_video_480p.mp4', command_str_hls)
        self.assertIn('-c:v copy', command_str_hls)
        self.assertIn('-c:a copy', command_str_hls)
        self.assertNotIn('-codec:copy', command_str_hls)

        self.assertEqual(mock_remove.call_count, 4)
