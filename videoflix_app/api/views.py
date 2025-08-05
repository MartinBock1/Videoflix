import os
import re
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
    authentication = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        videos = Video.objects.all()
        serializer = VideoSerializer(videos, many=True, context={'request': request})

        return Response(serializer.data)

class VideoDetailView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            video = Video.objects.get(pk=pk)
            serializer = VideoDetailSerializer(video, context={'request': request})
            return Response(serializer.data)
        except Video.DoesNotExist:
            return Response({'error': 'Video not found'}, status=status.HTTP_404_NOT_FOUND)
        

class HLSPlaylistView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution):
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
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id, resolution, segment):
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
