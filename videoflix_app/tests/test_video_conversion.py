import os
import tempfile
from subprocess import CalledProcessError, TimeoutExpired
from unittest.mock import patch, MagicMock, call
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.db.models.signals import post_save

from ..models import Video
from ..tasks import generate_thumbnail, convert_video_to_hls, cleanup_files
from .. import signals


FAKE_VIDEO_CONTENT = b'GIF89a\x01\x00\x01\x00\x00\x00\x00\x00'
TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix='videoflix_test_media_')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class VideoConversionTasksTest(TestCase):
    """
    Test suite for video conversion tasks.
    
    This class tests the actual conversion logic including:
    1. Thumbnail generation
    2. HLS conversion in multiple resolutions
    3. File cleanup
    4. Error handling
    """

    def setUp(self):
        """Set up test video for conversion tests."""
        # Disconnect signals to prevent Redis connection attempts during testing
        post_save.disconnect(signals.video_post_save, sender=Video)
        
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
        """Clean up temporary media directory and reconnect signals."""
        # Reconnect signals after test
        post_save.connect(signals.video_post_save, sender=Video)
        
        # More robust cleanup
        self._cleanup_temp_directories()
        
    def _cleanup_temp_directories(self):
        """Helper method to clean up all temporary test directories."""
        import glob
        import shutil
        
        # Cleanup the main temp directory
        if os.path.exists(TEMP_MEDIA_ROOT):
            shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        
        # Cleanup any additional temp directories created during tests
        temp_patterns = [
            '/tmp/videoflix_test_*',
            '/app/test_media',
        ]
        
        for pattern in temp_patterns:
            for temp_dir in glob.glob(pattern):
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)

    @patch('videoflix_app.tasks.subprocess.run')
    @patch('videoflix_app.tasks.os.makedirs')
    def test_generate_thumbnail_creates_correct_command(self, mock_makedirs, mock_subprocess):
        """Test that thumbnail generation creates the correct ffmpeg command."""
        mock_subprocess.return_value = MagicMock()
        
        generate_thumbnail(self.video.pk)
        
        # Verify subprocess was called
        self.assertTrue(mock_subprocess.called)
        
        # Get the command that was executed
        called_command = mock_subprocess.call_args[0][0]
        command_str = ' '.join(called_command)
        
        # Verify command contains expected ffmpeg parameters
        self.assertIn('ffmpeg', command_str)
        self.assertIn('-i', command_str)
        self.assertIn('test_video.mp4', command_str)
        self.assertIn('-ss 00:00:01.000', command_str)
        self.assertIn('-vframes 1', command_str)
        self.assertIn('.jpg', command_str)
        
        # Verify directory creation was attempted
        mock_makedirs.assert_called()

    @patch('videoflix_app.tasks.subprocess.run')
    def test_generate_thumbnail_handles_video_not_found(self, mock_subprocess):
        """Test thumbnail generation with non-existent video ID."""
        generate_thumbnail(9999)
        
        # Subprocess should not be called for non-existent video
        mock_subprocess.assert_not_called()

    @patch('videoflix_app.tasks.subprocess.run')
    def test_generate_thumbnail_skips_if_thumbnail_exists(self, mock_subprocess):
        """Test that thumbnail generation skips if thumbnail already exists."""
        # Set up video with existing thumbnail
        self.video.thumbnail_url.name = 'thumbnails/test_video.jpg'
        self.video.save()
        
        generate_thumbnail(self.video.pk)
        
        # Subprocess should not be called if thumbnail exists
        mock_subprocess.assert_not_called()

    @patch('videoflix_app.tasks.subprocess.run')
    def test_generate_thumbnail_handles_ffmpeg_error(self, mock_subprocess):
        """Test thumbnail generation error handling."""
        mock_subprocess.side_effect = CalledProcessError(1, 'ffmpeg', stderr='Error message')
        
        # Should not raise exception
        generate_thumbnail(self.video.pk)
        
        self.assertTrue(mock_subprocess.called)

    @patch('videoflix_app.tasks.cleanup_files')
    @patch('videoflix_app.tasks.subprocess.run')
    @patch('videoflix_app.tasks.os.makedirs')
    def test_convert_video_to_hls_creates_all_resolutions(self, mock_makedirs, mock_subprocess, mock_cleanup):
        """Test that HLS conversion creates all required resolutions."""
        mock_subprocess.return_value = MagicMock()
        
        convert_video_to_hls(self.video.pk)
        
        # Should be called 6 times total: 3 for MP4 creation + 3 for HLS conversion
        self.assertEqual(mock_subprocess.call_count, 6)
        
        # Check that all resolutions are processed
        all_calls = [call.args[0] for call in mock_subprocess.call_args_list]
        all_commands = [' '.join(cmd) for cmd in all_calls]
        
        # Verify MP4 creation commands
        mp4_commands = all_commands[:3]
        self.assertTrue(any('480p' in cmd for cmd in mp4_commands))
        self.assertTrue(any('720p' in cmd for cmd in mp4_commands))
        self.assertTrue(any('1080p' in cmd for cmd in mp4_commands))
        
        # Verify HLS conversion commands
        hls_commands = all_commands[3:]
        for cmd in hls_commands:
            self.assertIn('-c:v copy', cmd)
            self.assertIn('-c:a copy', cmd)
            self.assertIn('-f hls', cmd)
            self.assertIn('index.m3u8', cmd)

    @patch('videoflix_app.tasks.subprocess.run')
    def test_convert_video_to_hls_handles_video_not_found(self, mock_subprocess):
        """Test HLS conversion with non-existent video ID."""
        convert_video_to_hls(9999)
        
        # Subprocess should not be called for non-existent video
        mock_subprocess.assert_not_called()

    @patch('videoflix_app.tasks.cleanup_files')
    @patch('videoflix_app.tasks.subprocess.run')
    def test_convert_video_to_hls_handles_mp4_creation_error(self, mock_subprocess, mock_cleanup):
        """Test HLS conversion error handling during MP4 creation."""
        mock_subprocess.side_effect = CalledProcessError(1, 'ffmpeg', stderr='Error creating MP4')
        
        convert_video_to_hls(self.video.pk)
        
        # Should call cleanup after error
        mock_cleanup.assert_called()

    @patch('videoflix_app.tasks.subprocess.run')
    def test_convert_video_to_hls_command_structure(self, mock_subprocess):
        """Test the structure of ffmpeg commands for HLS conversion."""
        mock_subprocess.return_value = MagicMock()
        
        convert_video_to_hls(self.video.pk)
        
        # Get all command calls
        all_calls = [call.args[0] for call in mock_subprocess.call_args_list]
        
        # Test MP4 creation commands (first 3 calls)
        mp4_commands = all_calls[:3]
        for i, cmd in enumerate(mp4_commands):
            command_str = ' '.join(cmd)
            self.assertIn('ffmpeg -i', command_str)
            self.assertIn('-s', command_str)  # Scaling
            self.assertIn('-c:v libx264', command_str)  # Video codec
            self.assertIn('-crf 23', command_str)  # Quality
            self.assertIn('-c:a aac', command_str)  # Audio codec
        
        # Test HLS conversion commands (last 3 calls)
        hls_commands = all_calls[3:]
        for cmd in hls_commands:
            command_str = ' '.join(cmd)
            self.assertIn('ffmpeg -i', command_str)
            self.assertIn('-c:v copy -c:a copy', command_str)  # No re-encoding
            self.assertIn('-hls_segment_filename', command_str)
            self.assertIn('.ts', command_str)  # Segment files
            self.assertIn('-hls_time 10', command_str)  # 10-second segments

    @patch('videoflix_app.tasks.os.path.exists')
    @patch('videoflix_app.tasks.os.remove')
    def test_cleanup_files_removes_existing_files(self, mock_remove, mock_exists):
        """Test that cleanup_files removes all existing files."""
        mock_exists.return_value = True
        
        test_files = ['/path/to/file1.mp4', '/path/to/file2.mp4', '/path/to/file3.mp4']
        cleanup_files(test_files)
        
        # Should check existence of all files
        self.assertEqual(mock_exists.call_count, 3)
        
        # Should remove all existing files
        self.assertEqual(mock_remove.call_count, 3)
        expected_calls = [call(f) for f in test_files]
        mock_remove.assert_has_calls(expected_calls)

    @patch('videoflix_app.tasks.os.path.exists')
    @patch('videoflix_app.tasks.os.remove')
    def test_cleanup_files_skips_non_existent_files(self, mock_remove, mock_exists):
        """Test that cleanup_files skips non-existent files."""
        mock_exists.return_value = False
        
        test_files = ['/path/to/nonexistent1.mp4', '/path/to/nonexistent2.mp4']
        cleanup_files(test_files)
        
        # Should check existence but not try to remove
        self.assertEqual(mock_exists.call_count, 2)
        mock_remove.assert_not_called()

    @patch('videoflix_app.tasks.os.path.exists')
    @patch('videoflix_app.tasks.os.remove')
    def test_cleanup_files_handles_removal_error(self, mock_remove, mock_exists):
        """Test that cleanup_files handles OS errors gracefully."""
        mock_exists.return_value = True
        mock_remove.side_effect = OSError("Permission denied")
        
        test_files = ['/path/to/protected_file.mp4']
        
        # Should not raise exception
        cleanup_files(test_files)
        
        mock_remove.assert_called_once_with('/path/to/protected_file.mp4')

    def test_video_conversion_integration(self):
        """Integration test for the complete video conversion workflow."""
        with patch('videoflix_app.tasks.subprocess.run') as mock_subprocess, \
             patch('videoflix_app.tasks.os.makedirs') as mock_makedirs:
            
            mock_subprocess.return_value = MagicMock()
            
            # Test thumbnail generation
            generate_thumbnail(self.video.pk)
            
            # Test HLS conversion
            convert_video_to_hls(self.video.pk)
            
            # Verify total subprocess calls (1 for thumbnail + 6 for HLS)
            self.assertEqual(mock_subprocess.call_count, 7)
            
            # Verify directory creation was called
            self.assertTrue(mock_makedirs.called)

    @patch('videoflix_app.tasks.subprocess.run')
    def test_hls_conversion_resolution_dimensions(self, mock_subprocess):
        """Test that HLS conversion uses correct dimensions for each resolution."""
        mock_subprocess.return_value = MagicMock()
        
        convert_video_to_hls(self.video.pk)
        
        # Get MP4 creation commands (first 3 calls)
        mp4_commands = [' '.join(call.args[0]) for call in mock_subprocess.call_args_list[:3]]
        
        # Check that correct dimensions are used
        dimensions_found = []
        for cmd in mp4_commands:
            if '854x480' in cmd:
                dimensions_found.append('480p')
            elif '1280x720' in cmd:
                dimensions_found.append('720p')
            elif '1920x1080' in cmd:
                dimensions_found.append('1080p')
        
        self.assertEqual(len(dimensions_found), 3)
        self.assertIn('480p', dimensions_found)
        self.assertIn('720p', dimensions_found)
        self.assertIn('1080p', dimensions_found)

    @patch('videoflix_app.tasks.subprocess.run')
    def test_hls_conversion_timeout_handling(self, mock_subprocess):
        """Test that HLS conversion handles timeouts properly."""
        mock_subprocess.side_effect = TimeoutExpired('ffmpeg', 900)
        
        # Should not raise exception
        convert_video_to_hls(self.video.pk)
        
        # Should have attempted the first subprocess call
        self.assertTrue(mock_subprocess.called)
