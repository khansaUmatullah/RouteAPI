from django.contrib import admin
from django.urls import path, include

from source.views import RouteView

urlpatterns = [

    path('route/', RouteView.as_view(), name='route'),
]