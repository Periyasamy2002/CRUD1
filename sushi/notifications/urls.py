from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("list/", views.notifications_list, name="list"),
    path("mark-read/<int:pk>/", views.mark_read, name="mark_read"),
]
