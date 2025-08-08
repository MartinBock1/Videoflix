from django.db import models

# Create your models here.


class Video(models.Model):
    """
    Represents a video object in the database.

    This model stores all the essential information for a video, including its
    metadata, file paths for the video and its thumbnail, and categorization.
    """
    created_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail_url = models.FileField(upload_to='thumbnails/', blank=True, null=True)
    video_file = models.FileField(upload_to='videos/')
    category = models.CharField(max_length=100)

    def __str__(self):
        """
        Returns the string representation of the Video model.

        This is used in the Django admin interface and when printing the object,
        providing a human-readable name (the video's title).
        """
        return self.title
