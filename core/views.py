"""
Custom views to serve media files in development/Docker.
"""
import os
from django.conf import settings
from django.http import FileResponse, Http404
from django.views import View


class ServeMediaView(View):
    """
    View to serve media files when using Gunicorn in development.
    """
    
    def get(self, request, path):
        """
        Serve media files from MEDIA_ROOT.
        """
        file_path = os.path.join(settings.MEDIA_ROOT, path)
        
        # Check if file exists and is within MEDIA_ROOT
        if os.path.exists(file_path) and os.path.commonpath([settings.MEDIA_ROOT, file_path]) == str(settings.MEDIA_ROOT):
            return FileResponse(open(file_path, 'rb'))
        else:
            raise Http404("Media file not found.")
