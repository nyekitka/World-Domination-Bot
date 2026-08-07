from django.urls import path

from web_app.stats.views import render_stats

urlpatterns = [path('', render_stats)]
