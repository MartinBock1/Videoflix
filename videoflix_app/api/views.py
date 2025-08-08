import os, re
from django.http import FileResponse, Http404
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .serializers import VideoSerializer, VideoDetailSerializer
from ..models import Video
from user_auth_app.api.authentication import CookieJWTAuthentication


class VideoListView(APIView):
    """
    API view to retrieve a list of all available videos.

    Requires the user to be authenticated via a cookie-based JWT.
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to list all videos.

        Returns:
            Response: A DRF Response object containing the serialized video data.
        """
        videos = Video.objects.all()
        serializer = VideoSerializer(videos, many=True, context={'request': request})

        return Response(serializer.data)


class VideoDetailView(APIView):
    """
    API view to retrieve the details of a single video.

    Requires the user to be authenticated via a cookie-based JWT.
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """
        Handles GET requests for a single video identified by its primary key.

        Args:
            pk (int): The primary key of the video to retrieve.

        Returns:
            Response: A DRF Response with the video's details or a 404 error.
        """
        try:
            video = Video.objects.get(pk=pk)
            serializer = VideoDetailSerializer(video, context={'request': request})
            return Response(serializer.data)
        except Video.DoesNotExist:
            return Response({'error': 'Video not found'}, status=status.HTTP_404_NOT_FOUND)
        

class HLSPlaylistView(APIView):
    """
    API view to serve the HLS playlist file (.m3u8) for a video.

    This view constructs the path to the playlist file based on the video ID
    and the requested resolution.
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution):
        """
        Handles GET requests for an HLS playlist.

        Args:
            movie_id (int): The primary key of the video.
            resolution (str): The requested resolution (e.g., '1080p').

        Returns:
            FileResponse: A response streaming the .m3u8 file, or a 404 error.
        """
        try:
            video = Video.objects.get(pk=movie_id)
            base_filename = os.path.splitext(os.path.basename(video.video_file.name))[0]
            playlist_path = os.path.join(
                settings.MEDIA_ROOT,
                'videos',
                base_filename,
                resolution,
                'index.m3u8'
            )

            if os.path.exists(playlist_path):
                response = FileResponse(open(playlist_path, 'rb'),
                                        content_type='application/vnd.apple.mpegurl')
                return response
            else:
                raise Http404

        except Video.DoesNotExist:
            raise Http404


class HLSSegmentView(APIView):
    """
    API view to serve an HLS video segment file (.ts).

    This view constructs the path to a specific segment file based on the
    video ID, resolution, and segment name.
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution, segment):
        """
        Handles GET requests for an HLS video segment.

        Args:
            movie_id (int): The primary key of the video.
            resolution (str): The resolution of the segment.
            segment (str): The name of the segment file (e.g., '0001.ts').

        Returns:
            FileResponse: A response streaming the .ts file, or a 404 error.
        """
        if not re.match(r'\d+\.ts$', segment):
            raise Http404("Invalid segment format.")

        try:
            video = Video.objects.get(pk=movie_id)
            base_filename = os.path.splitext(os.path.basename(video.video_file.name))[0]
            segment_path = os.path.join(
                settings.MEDIA_ROOT,
                'videos',
                base_filename,
                resolution,
                segment
            )

            if os.path.exists(segment_path):
                response = FileResponse(open(segment_path, 'rb'), content_type='video/MP2T')
                return response
            else:
                raise Http404

        except Video.DoesNotExist:
            raise Http404
