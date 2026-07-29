from django.urls import path
from stats.views import render_stats

urlpatterns = [
    path('<int:game_id>/<int:round>/', render_stats)
]