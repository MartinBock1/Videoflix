from django.db import models

# Create your models here.
class Video(models.Model):
    created_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail_url = models.FileField(upload_to='thumbnails/')
    category = models.CharField(max_length=100)
    
    def __str__(self):
        return self.title