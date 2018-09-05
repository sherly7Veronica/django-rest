"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin

# from blog import views
from django.views.generic.base import RedirectView

urlpatterns = [
    url('admin/', admin.site.urls),

    url('api/(?P<version>(v1|v2))/', include('music.urls'), name="version")

    # url(r'^mysite/', include('myuser.urls', namespace='myuser')),

    # url(r'^polls/', include('polls.urls')),

    # url(r'^$', RedirectView.as_view(pattern_name='myrestaurants:restaurant_list'), name='home'),
    # url(r'^myrestaurants/', include('myrestaurants.urls', namespace='myrestaurants')),
    # url(r'^dishes')



    # url('^home', views.home, name='home'),
    # url('^blog/', views.post_list, name='blog'),

    # url('^signup/', views.signup, name='signup'),
    # url('^mysite/', views.mysite, name='mysite')
]
