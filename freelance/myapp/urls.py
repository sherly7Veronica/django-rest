from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'$/', views.AssetsListCreateAPIView.as_view(), name='list'),
    url(r'fulllist/$', views.AssestsListAPIView.as_view(), name='group')
]
