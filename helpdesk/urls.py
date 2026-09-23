from django.urls import path
from . import views

app_name = 'helpdesk'
urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.choose, name='choose'),
    path('new/<int:type_id>/', views.create, name='create'),
    path('tickets/<int:pk>/', views.detail, name='detail'),
    path('attachments/<int:pk>/', views.attachment, name='attachment'),
]
