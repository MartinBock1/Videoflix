from django.contrib import admin
from django.utils.html import format_html

from .models import Video

# Register your models here.
@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """
    Customizes the admin interface for the Video model.
    """
    list_display = (
        'title',
        'category',
        'created_at',
        'video_file',
        'thumbnail_preview'
    )
    
    readonly_fields = ('thumbnail_preview',)
    list_filter = ('category',)
    search_fields = ('title', 'description')
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'category', 'video_file')
        }),
        ('Vorschaubild (automatisch generiert)', {
            'fields': ('thumbnail_preview',),
        }),
    )

    readonly_fields = ('thumbnail_preview',)

    def thumbnail_preview(self, obj):
        """
        Creates an HTML img tag to display the thumbnail in the admin.

        This method is used for both the 'list_display' and the 'readonly_fields'.
        It checks if a thumbnail exists and has a URL.

        Args:
            obj: The Video instance.

        Returns:
            str: An HTML string for the image tag or a default message.
        """
        if obj.thumbnail_url and hasattr(obj.thumbnail_url, 'url'):
            return format_html(
                '<a href="{0}" target="_blank">'
                '<img src="{0}" style="max-height: 50px;" />'
                '</a>',
                obj.thumbnail_url.url
            )
        return "Wird nach dem Speichern generiert..."

    thumbnail_preview.short_description = 'Vorschau'
