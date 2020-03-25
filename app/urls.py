from app.views import *
from django.urls import path, include


urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('dashboard', DashboardView.as_view(), name='dashboard'),
    path('api/line/callback', LineBotApiView.as_view(), name='api.line.callback'),
]
