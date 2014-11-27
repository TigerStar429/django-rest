from __future__ import unicode_literals
from django.conf.urls import patterns, url
from django.test import TestCase
from django.utils import six
from rest_framework.utils.model_meta import _resolve_model
from rest_framework.utils.breadcrumbs import get_breadcrumbs
from rest_framework.views import APIView
from tests.models import BasicModel


class Root(APIView):
    pass


class ResourceRoot(APIView):
    pass


class ResourceInstance(APIView):
    pass


class NestedResourceRoot(APIView):
    pass


class NestedResourceInstance(APIView):
    pass


urlpatterns = patterns(
    '',
    url(r'^$', Root.as_view()),
    url(r'^resource/$', ResourceRoot.as_view()),
    url(r'^resource/(?P<key>[0-9]+)$', ResourceInstance.as_view()),
    url(r'^resource/(?P<key>[0-9]+)/$', NestedResourceRoot.as_view()),
    url(r'^resource/(?P<key>[0-9]+)/(?P<other>[A-Za-z]+)$', NestedResourceInstance.as_view()),
)


class BreadcrumbTests(TestCase):
    """
    Tests the breadcrumb functionality used by the HTML renderer.
    """
    urls = 'tests.test_utils'

    def test_root_breadcrumbs(self):
        url = '/'
        self.assertEqual(
            get_breadcrumbs(url),
            [('Root', '/')]
        )

    def test_resource_root_breadcrumbs(self):
        url = '/resource/'
        self.assertEqual(
            get_breadcrumbs(url),
            [
                ('Root', '/'),
                ('Resource Root', '/resource/')
            ]
        )

    def test_resource_instance_breadcrumbs(self):
        url = '/resource/123'
        self.assertEqual(
            get_breadcrumbs(url),
            [
                ('Root', '/'),
                ('Resource Root', '/resource/'),
                ('Resource Instance', '/resource/123')
            ]
        )

    def test_nested_resource_breadcrumbs(self):
        url = '/resource/123/'
        self.assertEqual(
            get_breadcrumbs(url),
            [
                ('Root', '/'),
                ('Resource Root', '/resource/'),
                ('Resource Instance', '/resource/123'),
                ('Nested Resource Root', '/resource/123/')
            ]
        )

    def test_nested_resource_instance_breadcrumbs(self):
        url = '/resource/123/abc'
        self.assertEqual(
            get_breadcrumbs(url),
            [
                ('Root', '/'),
                ('Resource Root', '/resource/'),
                ('Resource Instance', '/resource/123'),
                ('Nested Resource Root', '/resource/123/'),
                ('Nested Resource Instance', '/resource/123/abc')
            ]
        )

    def test_broken_url_breadcrumbs_handled_gracefully(self):
        url = '/foobar'
        self.assertEqual(
            get_breadcrumbs(url),
            [('Root', '/')]
        )


class ResolveModelTests(TestCase):
    """
    `_resolve_model` should return a Django model class given the
    provided argument is a Django model class itself, or a properly
    formatted string representation of one.
    """
    def test_resolve_django_model(self):
        resolved_model = _resolve_model(BasicModel)
        self.assertEqual(resolved_model, BasicModel)

    def test_resolve_string_representation(self):
        resolved_model = _resolve_model('tests.BasicModel')
        self.assertEqual(resolved_model, BasicModel)

    def test_resolve_unicode_representation(self):
        resolved_model = _resolve_model(six.text_type('tests.BasicModel'))
        self.assertEqual(resolved_model, BasicModel)

    def test_resolve_non_django_model(self):
        with self.assertRaises(ValueError):
            _resolve_model(TestCase)

    def test_resolve_improper_string_representation(self):
        with self.assertRaises(ValueError):
            _resolve_model('BasicModel')