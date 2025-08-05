from rest_framework import serializers
from django.urls import reverse

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

# class VideoDetailSerializer(VideoSerializer):
#     video_url = serializers.SerializerMethodField()

#     class Meta:
#         model = Video
#         fields = ['id', 'created_at', 'title', 'description', 'thumbnail_url', 'video_url', 'category']

#     def get_video_url(self, obj):
#         request = self.context.get('request')
#         if request and obj.video_file:
#             return request.build_absolute_uri(obj.video_file.url)
#         return ""


class VideoDetailSerializer(VideoSerializer):
    """
    Erweitert den VideoSerializer um ein Feld für die HLS-Playlist-URLs.
    """
    hls_urls = serializers.SerializerMethodField()

    class Meta(VideoSerializer.Meta):
        # Erbt alle Felder vom VideoSerializer und fügt 'hls_urls' hinzu.
        fields = VideoSerializer.Meta.fields + ['hls_urls']

    def get_hls_urls(self, obj):
        """
        Generiert ein Dictionary mit den HLS-Playlist-URLs für alle Auflösungen.
        """
        request = self.context.get('request')
        if not request:
            # Ohne Request-Kontext können keine absoluten URLs erstellt werden.
            return None

        urls = {}
        # Liste der Auflösungen, die wir anbieten.
        resolutions = ['480p', '720p', '1080p']

        for res in resolutions:
            # Verwendet den Namen der URL-Route ('hls-playlist'), um die URL dynamisch zu erstellen.
            # Dies ist robuster als das manuelle Zusammensetzen von Strings.
            relative_url = reverse('hls-playlist', kwargs={'movie_id': obj.pk, 'resolution': res})
            # Wandelt die relative URL (z.B. /api/video/1/480p/...) in eine absolute URL um.
            urls[res] = request.build_absolute_uri(relative_url)

        return urls
