# coding: utf-8

# $Id: $


class COPMixin(object):
    """ CacheOpsPages mixin for cache key generation and
    queryset dependency setup.
    Should be first mixin in inheritance.
    """

    def __init__(self, *args, **kwargs):
        super(COPMixin, self).__init__(*args, **kwargs)
        self.__querysets = []

    @classmethod
    def get_cache_key(cls, request):
        """ Generates cache key for page content caching."""
        return "CACHE:" + request.get_full_path()

    def depends_on(self, *querysets):
        """ Registers dependency between querysets and page content.
        """
        self.__querysets.extend(querysets)

    def get(self, request, *args, **kwargs):
        """ Sets cache key and querysets for processing in middleware."""
        response = super(COPMixin, self).get(request, *args, **kwargs)
        request.cache_key = self.get_cache_key(request)
        request.cache_querysets = self.__querysets
        return response
