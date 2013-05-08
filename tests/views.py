# coding: utf-8

# $Id: $
from django.http import Http404
from django.views.generic import TemplateView
from cacheops_pages.views import COPMixin
from models import Project


class TestView(COPMixin, TemplateView):
    template_name = 'test.html'

    def get_context_data(self, **kwargs):
        cd = super(TestView, self).get_context_data(**kwargs)
        try:
            project = Project.objects.get(pk=kwargs['pk'])
        except Project.DoesNotExist:
            raise Http404()
        cd['project'] = project
        self.depends_on(project)
        self.depends_on(project.module_set.all())
        return cd


class TestRelatedLookup(COPMixin, TemplateView):
    template_name = 'test.html'

    def get_context_data(self, **kwargs):
        cd = super(TestRelatedLookup, self).get_context_data(**kwargs)
        try:
            project = Project.objects.get(name=kwargs['name'])
        except Project.DoesNotExist:
            raise Http404()
        cd['project'] = project
        self.depends_on(Project.objects.filter(name=kwargs['name']))
        return cd