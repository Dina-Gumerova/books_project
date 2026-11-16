from django.urls import path
from . import views

app_name = "books"
urlpatterns = [
    path("", views.index, name="index"),
    path("download/", views.download_all, name="download_all"),
    path("download/<str:filename>/", views.download_file, name="download_file"),
]
