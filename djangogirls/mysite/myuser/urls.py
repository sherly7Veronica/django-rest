from django.conf.urls import url
from myuser import views

urlpatterns = [
    url(r'^create/', views.UserCreateView.as_view(), name="create"),
    url(r'^(?P<pk>\d+)/detail/', views.UserCreateView.as_view(), name="detail"),
    url(r'^(?P<pk>\d+)/update/', views.UserCreateView.as_view(), name="update"),
    url(r'^list/', views.UserCreateView.as_view(), name="list"),
    url(r'^(?P<pk>\d+)/delete/', views.UserCreateView.as_view(), name="delete")
]