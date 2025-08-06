import os
import tempfile
from unittest.mock import patch, call

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import TestCase, override_settings

from ..models import Video
from ..tasks import generate_thumbnail, convert_video_to_hls

# Create a small, valid binary content for a fake video file.
FAKE_VIDEO_CONTENT = b'GIF89a\x01\x00\x01\x00\x00\x00\x00\x00'
# Create a temporary directory for media files to use during tests.
# This ensures test isolation and avoids polluting the actual media root.
TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix='videoflix_test_media_')


# Decorator to override the MEDIA_ROOT setting for the duration of this test class.
# All file operations will be redirected to our temporary directory.
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class SignalsAndTasksTest(TestCase):
    """
    Test suite for Django signals and background tasks.

    This class tests that:
    1. The post_save signal correctly enqueues background tasks.
    2. The post_delete signal correctly cleans up associated files.
    3. The background task functions call their external dependencies (like ffmpeg)
       with the correct arguments.
    """

    def setUp(self):
        """
        Set up the test environment before each test method runs.
        """
        # Arrange: Create a fake video file in memory.
        fake_video_file = SimpleUploadedFile(
            "test_video.mp4",
            FAKE_VIDEO_CONTENT,
            content_type="video/mp4"
        )
        # Arrange: Create a Video object, which will save the fake file
        # to the temporary media root.
        self.video = Video.objects.create(
            title="Test Video",
            description="A test description",
            category="Testing",
            video_file=fake_video_file
        )

    def tearDown(self):
        """
        Clean up the temporary media directory after each test.
        """
        # This is a robust way to remove the temporary directory and its contents.
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
        """
        Test that creating a new Video object triggers the post_save signal
        and enqueues the thumbnail and HLS conversion tasks.
        """
        # Arrange: Set up the mock queue object that the signal will interact with.
        mock_queue = mock_get_queue.return_value
        new_video_file = SimpleUploadedFile("new.mp4", FAKE_VIDEO_CONTENT)

        # Act: Create a new video, which triggers the signal.
        new_video = Video.objects.create(
            title="New",
            description="d",
            category="c",
            video_file=new_video_file
        )

        # Assert: Check that the `enqueue` method was called with the correct tasks
        # and the primary key of the new video.
        expected_calls = [
            call('videoflix_app.tasks.generate_thumbnail', new_video.pk),
            call('videoflix_app.tasks.convert_video_to_hls', new_video.pk)
        ]
        mock_queue.enqueue.assert_has_calls(expected_calls, any_order=True)

    @patch('videoflix_app.signals.shutil.rmtree')
    @patch('videoflix_app.signals.os.remove')
    @patch('videoflix_app.signals.os.path.isfile', return_value=True)
    @patch('videoflix_app.signals.os.path.isdir', return_value=True)
    def test_post_delete_signal_removes_main_directory(
            self, mock_isdir, mock_isfile, mock_os_remove, mock_rmtree):
        """
        Test that deleting a Video object triggers the post_delete signal,
        which should attempt to remove the original file and HLS directory.
        """
        # Arrange: Calculate the paths that should be deleted.
        original_path = self.video.video_file.path
        base_filename = os.path.splitext(os.path.basename(original_path))[0]
        video_dir = os.path.dirname(original_path)
        expected_dir_to_delete = os.path.join(video_dir, base_filename)

        # Act: Delete the video object, which triggers the signal.
        self.video.delete()

        # Assert: Check that the file system removal functions were called
        # with the correct paths.
        mock_os_remove.assert_called_with(original_path)
        mock_rmtree.assert_called_with(expected_dir_to_delete)

    @patch('subprocess.run')
    def test_generate_thumbnail_task(self, mock_subprocess_run):
        """
        Test the thumbnail generation task to ensure it calls subprocess.run.
        """
        # Act: Call the task function directly with the video's pk.
        generate_thumbnail(self.video.pk)

        # Assert: Verify that the task attempted to run an external command.
        self.assertTrue(mock_subprocess_run.called)

    @patch('videoflix_app.tasks.os.remove')
    @patch('videoflix_app.tasks.os.path.exists', return_value=True)
    @patch('videoflix_app.tasks.subprocess.run')
    def test_convert_to_hls_task_logic(
            self, mock_subprocess_run, mock_exists, mock_remove):
        """
        Test the HLS conversion task's internal logic.
        """
        # Act: Call the task function directly.
        convert_video_to_hls(self.video.pk)

        # Assert: Check that ffmpeg was called for each resolution (3) and
        # then again for HLS conversion for each resolution (3), totaling 6 calls.
        self.assertEqual(mock_subprocess_run.call_count, 6)

        # Assert: Inspect the arguments of one of the HLS conversion calls
        # to ensure the command is constructed correctly.
        # This checks the 4th call (index 3), which is the first HLS conversion.
        call_args_hls = mock_subprocess_run.call_args_list[3].args[0]
        command_str_hls = ' '.join(call_args_hls)
        self.assertIn('test_video_480p.mp4', command_str_hls)
        # It should use 'copy' codec for speed as re-encoding is already done.
        self.assertIn('-c:v copy', command_str_hls)
        self.assertIn('-c:a copy', command_str_hls)
        self.assertNotIn('-codec:copy', command_str_hls)

        # Assert: Check that the cleanup function was called to remove the
        # temporary MP4s (3) and the original video file (1).
        self.assertEqual(mock_remove.call_count, 4)
