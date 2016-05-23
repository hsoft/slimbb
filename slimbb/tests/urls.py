from django.conf.urls import patterns, include

urlpatterns = patterns('',
    (r'^forum/', include('slimbb.urls', namespace='slimbb')),
)
