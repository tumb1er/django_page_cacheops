# coding: utf-8

# $Id: $
import re
import urlparse
from django.core.urlresolvers import resolve, Resolver404
from django.utils.importlib import import_module
from settings import CACHEOPS_PAGES


class CacheConfig(object):
    cache_conf = CACHEOPS_PAGES

    def __init__(self, request):
        self.view_name = None
        self.args = []
        self.kwargs = {}
        self.init(request)

    def init(self, request):
        self.get_view_name(request)
        self.conf = self.get_conf(request)
        if not self.conf:
            return
        self.context = self.get_cache_context(request)
        self.cache_key = self.get_cache_key()
        self.querysets = self.get_querysets()

    def get_view_name(self, request):
        try:
            match = resolve(request.get_full_path())
            view_class = match.func.func_closure[1].cell_contents
            self.args = match.args
            self.kwargs = match.kwargs
            self.view_name = '%s.%s' % (
                view_class.__module__, view_class.__name__)
        except (IndexError, AttributeError, Resolver404):
            return None, None

    def get_conf(self, request):
        if not self.view_name:
            self.conf = None
            return
        self.conf = self.cache_conf.get(self.view_name)
        if self.conf:
            return self.conf
        for k, v in self.cache_conf.items():
            if self.view_name.startswith(k):
                self.cache_conf[self.view_name] = v
                self.conf = v
        return self.conf

    def get_params(self, conf):
        for m in re.finditer(r"{([^}]+)}", conf['CACHE_KEY']):
            yield m.group(1)
        for _, filter_pattern in conf['DEPENDS_ON']:
            for v in filter_pattern.values():
                yield v

    def compute(self, param, request):
        full_path = request.get_full_path()
        try:
            path, query = full_path.split('?', 1)
        except ValueError:
            path = full_path
            query = ''
        query = dict(urlparse.parse_qsl(query))
        headers = request.META
        args = {}
        for i in range(len(self.args)):
            args[i] = self.args
        kwargs = self.kwargs
        ctx = locals()
        try:
            source, key = param.split('__', 1)
        except ValueError:
            return ctx.get(param)

        try:
            return ctx[source].get(key)
        except KeyError:
            return

    def get_cache_context(self, request):
        context = {}
        for param in self.get_params(self.conf):
            context[param] = self.compute(param, request)
        return context

    def get_cache_key(self):
        ctx = {k: v or '' for k, v in self.context.items()}
        return self.conf['CACHE_KEY'].format(**ctx)

    def get_querysets(self):
        result = []
        for dependency in self.conf['DEPENDS_ON']:
            model_name, filter_pattern = dependency
            module, model_name = model_name.rsplit('.', 1)
            module = import_module(module)
            model = getattr(module, model_name)
            filter = {k: self.context.get(v) for k, v in filter_pattern.items()}
            result.append(model.objects.filter(**filter))
        return result
