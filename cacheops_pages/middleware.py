# coding: utf-8

# $Id: $
from django.db.models import Model
from cacheops.conf import redis_client, model_profile
from cacheops.invalidation import conj_cache_key, cache_schemes
from cacheops.utils import non_proxy, conj_scheme, dnf


def cache_page_by_queryset(model, cache_key, data, cond_dnf=[[]], timeout=None,
                           only_conj=False):
    model = non_proxy(model)

    if timeout is None:
        profile = model_profile(model)
        timeout = profile['timeout']

    # Ensure that all schemes of current query are "known"
    schemes = map(conj_scheme, cond_dnf)
    cache_schemes.ensure_known(model, schemes)

    txn = redis_client.pipeline()

    # Here was data pickling, we don't need it because of caching string

    # Set data only for first queryset
    if not only_conj:
        if timeout is not None:
            txn.setex(cache_key, timeout, data)
        else:
            txn.set(cache_key, data)

    # Add new cache_key to list of dependencies for every conjunction in dnf
    for conj in cond_dnf:
        conj_key = conj_cache_key(model, conj)
        txn.sadd(conj_key, cache_key)
        if timeout is not None:
            # Invalidator timeout should be larger than timeout of any key it references
            # So we take timeout from profile which is our upper limit
            # Add few extra seconds to be extra safe
            txn.expire(conj_key, model._cacheprofile['timeout'] + 10)

    txn.execute()


def cache_page(cache_key, cache_querysets, content):
    only_conj = False
    for object_or_queryset in cache_querysets:
        if isinstance(object_or_queryset, Model):
            model = object_or_queryset.__class__
            objects = getattr(model, 'objects')
            qs = objects.filter(pk=object_or_queryset.pk)
        else:
            qs = object_or_queryset
        conj_dnf = dnf(qs)
        cache_page_by_queryset(qs.model, cache_key, content,
                               conj_dnf, only_conj=only_conj)
        only_conj = True


class CacheopsPagesMiddleware(object):
    def process_response(self, request, response):
        if (response.status_code == 200
            and request.method == 'GET'
            and hasattr(response, "cache_key")):
            cache_page(response.cache_key, response.cache_querysets,
                       response.content)
        return response
