from django.db import models

# Create your models here.


class Video(models.Model):
    """
    Represents a video object in the database.

    This model stores all the essential information for a video, including its
    metadata, file paths for the video and its thumbnail, and categorization.
    """
    # A timestamp that is automatically updated every time the object is saved.
    # It effectively tracks the last modification time.
    created_at = models.DateTimeField(auto_now=True)
    
    # A short, descriptive title for the video.
    title = models.CharField(max_length=255)
    
    # A longer text field for a detailed description or summary of the video.
    description = models.TextField()
    
    # A file path to the video's thumbnail image.
    # The file will be uploaded to the 'thumbnails/' directory within MEDIA_ROOT.
    # 'blank=True' and 'null=True' make this field optional in forms and the database.
    thumbnail_url = models.FileField(upload_to='thumbnails/', blank=True, null=True)
    
    # A required file path to the actual video file.
    # The file will be uploaded to the 'videos/' directory within MEDIA_ROOT.
    video_file = models.FileField(upload_to='videos/')
    
    # A field to categorize the video, e.g., 'Action', 'Comedy', 'Tutorial'.
    category = models.CharField(max_length=100)

    def __str__(self):
        """
        Returns the string representation of the Video model.

        This is used in the Django admin interface and when printing the object,
        providing a human-readable name (the video's title).
        """
        return self.title
