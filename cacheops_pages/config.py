# coding: utf-8

# $Id: $
import re
import urlparse
from django.core.urlresolvers import resolve, Resolver404
from django.utils.importlib import import_module
from settings import CACHEOPS_PAGES


class CacheConfig(object):
    cache_conf = CACHEOPS_PAGES

    def __init__(self, request, view_func, view_args, view_kwargs):
        self.view_name = None
        self.args = []
        self.kwargs = {}
        self.context = None
        self.init(request, view_func, view_args, view_kwargs)

    def init(self, request, view_func, view_args, view_kwargs):
        self.get_view_name(view_func)
        self.args = view_args
        self.kwargs = view_kwargs
        self.config = self.get_conf()
        if self.config:
            self.context = self.get_cache_context(request)

    def get_view_name(self, view_func):
        try:
            view_class = view_func.func_closure[1].cell_contents
            self.view_name = '%s.%s' % (
                view_class.__module__, view_class.__name__)
        except (IndexError, AttributeError, Resolver404):
            return None, None

    def get_conf(self):
        if not self.view_name:
            self.config = None
            return
        self.config = self.cache_conf.get(self.view_name)
        if self.config:
            return self.config
        for k, v in self.cache_conf.items():
            if self.view_name.startswith(k):
                self.cache_conf[self.view_name] = v
                self.config = v
        return self.config

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
        headers = {k.lower(): v for k, v in request.META.items()}
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
        for param in self.get_params(self.config):
            context[param] = self.compute(param, request)
        return context

    def get_cache_key(self):
        ctx = {k: v or '' for k, v in self.context.items()}
        return self.config['CACHE_KEY'].format(**ctx)

    def get_querysets(self):
        result = []
        for dependency in self.config['DEPENDS_ON']:
            model_name, filter_pattern = dependency
            module, model_name = model_name.rsplit('.', 1)
            module = import_module(module)
            model = getattr(module, model_name)
            filter = {k: self.context.get(v) for k, v in filter_pattern.items()}
            result.append(model.objects.filter(**filter))
        return result
