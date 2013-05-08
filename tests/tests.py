# coding: utf-8

# $Id: $
from django.core.urlresolvers import reverse

from django.test import TestCase
from cacheops import invalidate_obj
import cacheops.conf
from models import Project, Module
from views import TestView


class COPTestBase(TestCase):
    def get_url(self):
        return reverse('test', args=(self.project.pk,))

    def setUp(self):
        self.project = Project.objects.create(name="project")
        self.m1 = Module.objects.create(project=self.project, name="m1")
        self.m2 = Module.objects.create(project=self.project, name="m2")
        self.url = self.get_url()
        self.response = self.client.get(self.url)
        self.redis = cacheops.conf.redis_client
        self.cache_key = TestView.get_cache_key(self.response._request)
        self.cache_content = self.redis.get(self.cache_key)

    def assertPageInvalidated(self):
        cache_content = self.redis.get(self.cache_key)
        self.assertIsNone(cache_content)

    def tearDown(self):
        self.redis.flushdb()


class CachingTestCase(COPTestBase):

    def testCacheKeyExists(self):
        """ Проверяет, что кэш наполняется."""
        self.assertIsNotNone(self.cache_content)

    def testCacheDiffersByUrl(self):
        """ Проверяет, что кэш отличается для разных URL."""
        p2 = Project.objects.create(name="another")
        Module.objects.create(project=p2, name="m3")
        self.url = reverse('test', args=(p2.pk,))
        response = self.client.get(self.url)
        cache_key = TestView.get_cache_key(response._request)
        cache_content = self.redis.get(cache_key)
        self.assertNotEqual(cache_content, self.cache_content)

    def testNotCacheFor404(self):
        """ Проверяет, что кэширование работает только для HTTP_200_OK."""
        self.url = reverse('test', args=(2,))
        self.client.get(self.url)
        pk = str(self.project.pk)
        cache_content = self.redis.get(self.cache_key.replace(pk, '2'))
        self.assertIsNone(cache_content)


class InvalidationTestCase(COPTestBase):

    def testInvalidateObj(self):
        """ Проверяет инвалидацию страницы на вызов cacheops.invalidate_obj."""
        invalidate_obj(self.project)
        self.assertPageInvalidated()

    def testInvalidateOnChange(self):
        """ Проверяет инвалидацию страницы при изменении объекта."""
        self.project.name = "another"
        self.project.save()
        self.assertPageInvalidated()

    def testInvalidateOnFKChange(self):
        """ Проверяет инвалидацию страницы при изменении внешнего ключа."""
        p2 = Project.objects.create(name='another')
        self.m2.project = p2
        self.m2.save()
        self.assertPageInvalidated()


class RelatedLookupTestCase(COPTestBase):
    def get_url(self):
        return reverse('related', args=('project',))

    def testCacheKeyExists(self):
        self.assertIsNotNone(self.cache_content)

    def testInvalidateOnChange(self):
        """ Проверяет инвалидацию страницы при изменении объекта."""
        self.project.name = "another"
        self.project.save()
        self.assertPageInvalidated()


class ConfigViewTestCase(COPTestBase):
    def get_url(self):
        return reverse('config', args=(self.m1.pk,))