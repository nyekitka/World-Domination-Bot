from django.urls import path

from web_app.stats import views

urlpatterns = [
    path(
        '<int:game_id>/<int:round_num>/',
        views.round_stats_page,
        name='stats_page',
    ),
    path(
        'api/stats/<int:game_id>/<int:round_num>/',
        views.get_round_stats_api,
        name='stats_api',
    ),
    path(
        'forbidden/',
        views.custom_403_view,
        name='stats_api',
    ),
]