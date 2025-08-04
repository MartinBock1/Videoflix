from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .serializers import VideoSerializer
from ..models import Video
from user_auth_app.api.authentication import CookieJWTAuthentication


class VideoListView(APIView):
    authentication = [CookieJWTAuthentication]
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        videos = Video.objects.all()
        serializer = VideoSerializer(videos, many=True, context={'request': request})
        
        return Response(serializer.data)
