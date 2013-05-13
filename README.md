Django-Page-Cacheops
====================

Redis page cache with invalidation from [django-cacheops](https://github.com/Suor/django-cacheops)

The biggest problem for http responses caching is invalidation. Django-cachops application enables queryset caching with smart invalidation.
In example, when you change any field of some user, it deletes all cached querysets filtered with old or new value of changed field, so cache remains consistent.
Same logic can be applyed to response caching, when front-end server (apache or nginx) doesn't request django backend at all.

In two words
------------

To cache page content with proper invalidation you must:
1. determine querysets affecting this page 
2. set redis cache key with page content
3. tell cacheops to invalidate this cache key when any of querysets has been invalidated
4. setup frontend to use redis cache

Configuration
------------

1. Add django-cacheops and cacheops_pages to INSTALLED_APPS

    INSTALLED_APPS += (
        'cacheops',
        'cacheops_pages',
    )

2. Configure cacheops [See README](https://github.com/Suor/django-cacheops/blob/master/README.rst)
3. Add cacheops-pages empty config

    CACHEOPS_PAGES = {}

4. Add middleware:

    MIDDLEWARE_CLASSES += (
        'cacheops_pages.middleware.CacheopsPagesMiddleware',
    )

Limitations
-----------

1. Only GET and only HTTP_200_OK responses are cached.
2. Only class-based views are cached

Example for generic views
-------------------------

1. Add COPMixin to cached view

    from cacheops_pages.views import COPMixin
    class TestView(COPMixin, TemplateView):
        ....

2. Call self.depends_on to tell which querysets affect view response
    
    project = Project.objects.get(pk=kwargs['pk'])
    self.depends_on(project)
    self.depends_on(project.module_set.all())

3. Setup frontend to use redis cache for it

with [redis2-nginx-module](https://github.com/agentzh/redis2-nginx-module)

    # GET /get?param=value
    location /get {
        redis2_query get $key$arg_param;
        redis2_pass foo.com:6379;
    }

This code is more intellectual than configuring caching CACHEOPS_PAGES, but you will not be able to change caching in production without deploying new release.

Example for CACHEOPS_PAGES
--------------------------

No mixins needed, only middleware. This example will show cache config for url `/test/view/(P<?pk>\d+)`

    CACHEOPS_PAGES = {
        'views.TestConfigView': {                                       # View name for caching
            'CACHE_KEY': 'CACHE:{path}{query__param}{headers__accept}', # Cache key template
            'DEPENDS_ON': (                                             # List of querysets affecting page content
                ('models.Project', {'pk': 'kwargs__pk'}),                   
                ('models.Module', {'project': 'kwargs__pk'}),
            )
        }
    }

In config you could use these variables:

1. `path` path without query params, in example `/test/view/1/`
2. `full_path`, path with query, in example `/test/view/1/?param=3`
3. `query_string`, containing all query params.
4. `query__<key>` which contains value of <key> parameter in query string, in example `query__param` returns 3
5. `kwargs__<key>` which contains value of <key> keyword argument passed to the view from url dispatcher, in example, `kwargs__pk` returns 1
6. `args__<i>` which contains <i> `args` item passed to the view from url dispatcher.
7. `headers__<key>` which contains value of <key> header from http request, in example:

    GET /test/view/1/?param=3 HTTP/1.1
    Accept: text/html

`headers__accept` returns "text/html"
