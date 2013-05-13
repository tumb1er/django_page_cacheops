# coding: utf-8

# $Id: $
from django.db.models import Model
from cacheops.conf import redis_client, model_profile
from cacheops.invalidation import conj_cache_key, cache_schemes
from cacheops.utils import non_proxy, conj_scheme, dnf
from config import CacheConfig


def cache_page_by_queryset(model, cache_key, data, cond_dnf=[[]], timeout=None,
                           only_conj=False):
    """ Overridden method `cacheops.query.cache_thing` which doesn't
    pickle data and can set only invalidation conjunctions.
    """
    model = non_proxy(model)

    if timeout is None:
        profile = model_profile(model)
        timeout = profile['timeout']

    schemes = map(conj_scheme, cond_dnf)
    cache_schemes.ensure_known(model, schemes)

    txn = redis_client.pipeline()

    # Here was data pickling, we don't need it because of caching raw value
    # pickled_data = pickle.dumps(data, -1)

    # Check whether setting data is allowed in `only_conj` argument
    if not only_conj:
        if timeout is not None:
            txn.setex(cache_key, timeout, data)
        else:
            txn.set(cache_key, data)

    for conj in cond_dnf:
        conj_key = conj_cache_key(model, conj)
        txn.sadd(conj_key, cache_key)
        if timeout is not None:
            txn.expire(conj_key, model._cacheprofile['timeout'] + 10)

    txn.execute()


def get_cache_timeout(queryset):
    """ Gets CacheOps cache timeout for model."""
    try:
        return queryset._cacheprofile.get('timeout')
    except AttributeError:
        return


def cache_page(cache_key, cache_querysets, content):
    """ Sets page cache content and adds invalidators for cache_querysets."""
    only_conj = False
    min_timeout = None
    querysets = []
    for object_or_queryset in cache_querysets:
        # Getting queryset for model instance or queryset
        if isinstance(object_or_queryset, Model):
            # ConcreteModel.objects.filter(pk=obj.pk)
            model = object_or_queryset.__class__
            objects = getattr(model, 'objects')
            qs = objects.filter(pk=object_or_queryset.pk)
        else:
            qs = object_or_queryset
        querysets.append(qs)
        timeout = get_cache_timeout(qs)
        if not min_timeout or min_timeout > timeout:
            min_timeout = timeout
    for qs in querysets:
        # Computing DNF for queryset
        # (see `cacheops.query.QuerySetMixin._cache_results`)
        conj_dnf = dnf(qs)
        timeout = get_cache_timeout(qs)
        # Set cache key value only for minimum timeout
        cache_data = not min_timeout or timeout == min_timeout
        cache_page_by_queryset(qs.model, cache_key, content,
                               conj_dnf, only_conj=not cache_data)


class CacheopsPagesMiddleware(object):
    """ Page cache setter middleware."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        """ Searches `CacheConfig` for `view_func` and set computed values
        for cache_key and cache_querysets in request from CACHEOPS_PAGES.
        """
        cache_config = CacheConfig(request, view_func, view_args, view_kwargs)
        if cache_config.config:
            request.cache_key = cache_config.get_cache_key()
            request.cache_querysets = cache_config.get_querysets()

    def process_response(self, request, response):
        """ Caches page content in redis if needed.
        """
        if not (response.status_code == 200 and request.method == 'GET'):
            return response
        if hasattr(request, "cache_key"):
            cache_page(request.cache_key, request.cache_querysets,
                       response.content)
            return response
