from django.conf.urls import url
from puppies import views


urlpatterns = [
    url(
        r'^api/vi/puppies/(?P<pk>[0-9]+)$',
        views.get_delete_update_puppy,
        name='get_delete_update_puppy'
    ),
    url(
        r'^api/vi/puppies/$',
        views.get_post_puppies,
        name='get_post_puppies'
    )
]