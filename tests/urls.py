from django.conf.urls.defaults import patterns, url

from views import TestView, TestRelatedLookup

urlpatterns = patterns(
    '',
    url(r'^project/(?P<pk>\d+)', TestView.as_view(), name="test"),
    url(r'^project/(?P<name>\w+)', TestRelatedLookup.as_view(), name="related"),

)
