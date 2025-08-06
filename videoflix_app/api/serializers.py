from rest_framework import serializers
from django.urls import reverse

from ..models import Video


class VideoSerializer(serializers.ModelSerializer):
    """
    Serializer for the Video model.

    Includes basic video information like ID, creation timestamp, title,
    description, thumbnail URL, and category.
    """
    # A read-only field that returns the URL of the video's thumbnail.
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
        # Get the request object from the serializer context.
        request = self.context.get('request')
        if request is None:
            # If no request is available, return None, indicating
            # the URL cannot be constructed.
            return None

        if obj.thumbnail_url:
            # Build the absolute URI from the thumbnail URL.
            return request.build_absolute_uri(obj.thumbnail_url.url)

        # If no thumbnail URL exists, return an empty string.
        return ""


class VideoDetailSerializer(VideoSerializer):
    """
    Serializer for detailed video information.

    Inherits from VideoSerializer and adds HLS (HTTP Live Streaming) URLs
    for different resolutions.
    """
    # A read-only field that returns a dictionary of HLS URLs.
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
        # Get the request object from the serializer context.
        request = self.context.get('request')
        if not request:
            # If no request is available, return None, indicating the
            # URLs cannot be constructed.
            return None

        urls = {}
        resolutions = ['480p', '720p', '1080p']

        for res in resolutions:
            # Build the relative URL using the 'hls-playlist' URL pattern name.
            relative_url = reverse(
                'hls-playlist',
                kwargs={'movie_id': obj.pk, 'resolution': res}
            )
            # Build the absolute URI using the relative URL.
            urls[res] = request.build_absolute_uri(relative_url)

        return urls
