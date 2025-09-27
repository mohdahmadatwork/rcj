from django.http import FileResponse, Http404
from django.conf import settings
from django.views import View
import os

class MediaServeView(View):
    def get(self, request, path):
        media_root = settings.MEDIA_ROOT
        file_path = os.path.join(media_root, path)
        if not os.path.exists(file_path):
            raise Http404("Media file not found.")
        return FileResponse(open(file_path, 'rb'))

# In your urls.py, add:
# from jewelry_orders.views import MediaServeView
# from django.urls import path
# urlpatterns += [
#     path('media/<path:path>/', MediaServeView.as_view(), name='media-serve'),
# ]