from rest_framework import serializers
from ..models import Video


class VideoSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = ['id', 'created_at', 'title', 'description', 'thumbnail_url', 'category']
    
    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if request is None:
            return None

        if obj.thumbnail_url:
            return request.build_absolute_uri(obj.thumbnail_url.url)
        
        return ""
    
class VideoDetailSerializer(VideoSerializer):
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ['id', 'created_at', 'title', 'description', 'thumbnail_url', 'video_url', 'category']

    def get_video_url(self, obj):
        request = self.context.get('request')
        if request and obj.video_file:
            return request.build_absolute_uri(obj.video_file.url)
        return ""
