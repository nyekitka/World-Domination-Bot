from django.urls import path

from web_app.stats import views

urlpatterns = [
    path(
        '<int:game_id>/<int:round_num>/',
        views.get_round_stats,
        name='stats_api',
    ),
]