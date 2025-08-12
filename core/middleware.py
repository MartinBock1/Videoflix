"""
Custom middleware to serve media files in development/Docker.
In production, use Nginx/Apache to serve media files.
"""
import os
from django.conf import settings
from django.http import FileResponse, Http404
from django.urls import resolve, Resolver404


class ServeMediaMiddleware:
    """
    Middleware to serve media files when using Gunicorn in development.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if request is for media files
        if request.path.startswith(settings.MEDIA_URL):
            return self.serve_media(request)
        
        response = self.get_response(request)
        return response

    def serve_media(self, request):
        """
        Serve media files from MEDIA_ROOT.
        """
        # Remove MEDIA_URL prefix to get relative path
        relative_path = request.path[len(settings.MEDIA_URL):]
        file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        
        # Check if file exists and is within MEDIA_ROOT
        if os.path.exists(file_path) and os.path.commonpath([settings.MEDIA_ROOT, file_path]) == settings.MEDIA_ROOT:
            return FileResponse(open(file_path, 'rb'))
        else:
            raise Http404("Media file not found.")
