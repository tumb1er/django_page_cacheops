# coding: utf-8

# $Id: $


class COPMixin(object):
    """ Миксин, реализующий функциональность кэширования страницы
    и указания зависимостей от QuerySet-ов для инвалидации.
    """

    def __init__(self, *args, **kwargs):
        super(COPMixin, self).__init__(*args, **kwargs)
        self.__querysets = []

    @classmethod
    def get_cache_key(cls, request):
        """ Генерирует ключ редиса, под которым будет кэшироваться
        контент страницы.
        """
        return "CACHE:" + request.get_full_path()

    def depends_on(self, *querysets):
        """ Регистрирует зависимость контента страницы от списка queryset-ов.
        """
        self.__querysets.extend(querysets)

    def get(self, request, *args, **kwargs):
        response = super(COPMixin, self).get(request,*args, **kwargs)
        request.cache_key = self.get_cache_key(request)
        request.cache_querysets = self.__querysets
        return response
