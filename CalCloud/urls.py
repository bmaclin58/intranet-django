from django.urls import path

from . import views

app_name = 'calcloud'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('assets/', views.assets, name='assets'),
    path('asset-tracker/', views.tracker, name='tracker'),
    path('asset-tracker/list/', views.tracking_list, name='tracking_list'),
    path('asset-tracker/<str:record_id>/', views.tracking_detail, name='tracking_detail'),
    path('recalls/', views.recalls, name='recalls'),
    path('help/', views.help_support, name='help'),
    path('changelog/', views.changelog, name='changelog'),
]
