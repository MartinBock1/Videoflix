from rest_framework import serializers
from django.urls import reverse

from ..models import Video


class VideoSerializer(serializers.ModelSerializer):
    """
    Serializer for the Video model.

    Includes basic video information like ID, creation timestamp, title,
    description, thumbnail URL, and category.
    """
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        """Meta class to define the model and fields to be serialized."""
        model = Video
        fields = [
            'id',
            'created_at',
            'title',
            'description',
            'thumbnail_url',
            'category'
        ]

    def get_thumbnail_url(self, obj):
        """
        Returns the absolute URL of the video's thumbnail.

        If a thumbnail URL exists and a request context is available,
        it constructs the absolute URL. Otherwise, it returns an empty string.

        Args:
            obj: The Video object being serialized.

        Returns:
            str: The absolute URL of the thumbnail, or an empty string.
        """
        request = self.context.get('request')
        if request is None:
            return None

        if obj.thumbnail_url:
            return request.build_absolute_uri(obj.thumbnail_url.url)

        return ""


class VideoDetailSerializer(VideoSerializer):
    """
    Serializer for detailed video information.

    Inherits from VideoSerializer and adds HLS (HTTP Live Streaming) URLs
    for different resolutions.
    """
    hls_urls = serializers.SerializerMethodField()

    class Meta(VideoSerializer.Meta):
        """
        Meta class to extend the fields from VideoSerializer.

        This ensures all fields from the base serializer are included.
        """
        fields = VideoSerializer.Meta.fields + ['hls_urls']

    def get_hls_urls(self, obj):
        """
        Returns a dictionary of HLS URLs for different resolutions.

        Constructs URLs for 480p, 720p, and 1080p resolutions.

        Args:
            obj: The Video object being serialized.

        Returns:
            dict: A dictionary containing HLS URLs for each resolution.
                 Example: {'480p': 'http://...', '720p': 'http://...', ...}
        """
        request = self.context.get('request')
        if not request:
            return None

        urls = {}
        resolutions = ['480p', '720p', '1080p']

        for res in resolutions:
            relative_url = reverse(
                'hls-playlist',
                kwargs={'movie_id': obj.pk, 'resolution': res}
            )
            urls[res] = request.build_absolute_uri(relative_url)

        return urls
