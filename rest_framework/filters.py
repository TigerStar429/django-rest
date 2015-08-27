"""
Provides generic filtering backends that can be used to filter the results
returned by list views.
"""
from __future__ import unicode_literals

import operator
from functools import reduce

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.template import Context, Template, loader
from django.utils import six

from rest_framework.compat import (
    distinct, django_filters, get_model_name, guardian
)
from rest_framework.settings import api_settings

FilterSet = django_filters and django_filters.FilterSet or None


class BaseFilterBackend(object):
    """
    A base class from which all filter backend classes should inherit.
    """

    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        raise NotImplementedError(".filter_queryset() must be overridden.")


class DjangoFilterBackend(BaseFilterBackend):
    """
    A filter backend that uses django-filter.
    """
    default_filter_set = FilterSet
    template = 'rest_framework/filters/django_filter.html'

    def __init__(self):
        assert django_filters, 'Using DjangoFilterBackend, but django-filter is not installed'

    def get_filter_class(self, view, queryset=None):
        """
        Return the django-filters `FilterSet` used to filter the queryset.
        """
        filter_class = getattr(view, 'filter_class', None)
        filter_fields = getattr(view, 'filter_fields', None)

        if filter_class:
            filter_model = filter_class.Meta.model

            assert issubclass(queryset.model, filter_model), \
                'FilterSet model %s does not match queryset model %s' % \
                (filter_model, queryset.model)

            return filter_class

        if filter_fields:
            from crispy_forms.helper import FormHelper
            from crispy_forms.layout import Field, Fieldset, Layout, Submit

            class AutoFilterSet(self.default_filter_set):
                class Meta:
                    model = queryset.model
                    fields = filter_fields

                @property
                def form(self):
                    self._form = super(AutoFilterSet, self).form
                    for field in self._form.fields.values():
                        field.help_text = None
                    layout_components = filter_fields + [
                        Submit('', 'Apply', css_class='btn-default'),
                    ]

                    helper = FormHelper()
                    helper.form_method = 'get'
                    helper.form_action = '.'
                    helper.template_pack = 'bootstrap3'

                    helper.layout = Layout(*layout_components)

                    self._form.helper = helper
                    return self._form

            return AutoFilterSet

        return None

    def filter_queryset(self, request, queryset, view):
        filter_class = self.get_filter_class(view, queryset)

        if filter_class:
            return filter_class(request.query_params, queryset=queryset).qs

        return queryset

    def to_html(self, request, queryset, view):
        cls = self.get_filter_class(view, queryset)
        filter_instance = cls(request.query_params, queryset=queryset)
        context = Context({
            'filter': filter_instance
        })
        template = loader.get_template(self.template)
        return template.render(context)


class SearchFilter(BaseFilterBackend):
    # The URL query parameter used for the search.
    search_param = api_settings.SEARCH_PARAM

    def get_search_terms(self, request):
        """
        Search terms are set by a ?search=... query parameter,
        and may be comma and/or whitespace delimited.
        """
        params = request.query_params.get(self.search_param, '')
        return params.replace(',', ' ').split()

    def construct_search(self, field_name):
        if field_name.startswith('^'):
            return "%s__istartswith" % field_name[1:]
        elif field_name.startswith('='):
            return "%s__iexact" % field_name[1:]
        elif field_name.startswith('@'):
            return "%s__search" % field_name[1:]
        if field_name.startswith('$'):
            return "%s__iregex" % field_name[1:]
        else:
            return "%s__icontains" % field_name

    def filter_queryset(self, request, queryset, view):
        search_fields = getattr(view, 'search_fields', None)

        search_terms = self.get_search_terms(request)

        if not search_fields or not search_terms:
            return queryset

        orm_lookups = [
            self.construct_search(six.text_type(search_field))
            for search_field in search_fields
        ]

        base = queryset
        for search_term in search_terms:
            queries = [
                models.Q(**{orm_lookup: search_term})
                for orm_lookup in orm_lookups
            ]
            queryset = queryset.filter(reduce(operator.or_, queries))

        # Filtering against a many-to-many field requires us to
        # call queryset.distinct() in order to avoid duplicate items
        # in the resulting queryset.
        return distinct(queryset, base)


class OrderingFilter(BaseFilterBackend):
    # The URL query parameter used for the ordering.
    ordering_param = api_settings.ORDERING_PARAM
    ordering_fields = None
    template = 'rest_framework/filters/ordering.html'

    def get_ordering(self, request, queryset, view):
        """
        Ordering is set by a comma delimited ?ordering=... query parameter.

        The `ordering` query parameter can be overridden by setting
        the `ordering_param` value on the OrderingFilter or by
        specifying an `ORDERING_PARAM` value in the API settings.
        """
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(',')]
            ordering = self.remove_invalid_fields(queryset, fields, view)
            if ordering:
                return ordering

        # No ordering was included, or all the ordering fields were invalid
        return self.get_default_ordering(view)

    def get_default_ordering(self, view):
        ordering = getattr(view, 'ordering', None)
        if isinstance(ordering, six.string_types):
            return (ordering,)
        return ordering

    def get_valid_fields(self, queryset, view):
        valid_fields = getattr(view, 'ordering_fields', self.ordering_fields)

        if valid_fields is None:
            # Default to allowing filtering on serializer fields
            serializer_class = getattr(view, 'serializer_class')
            if serializer_class is None:
                msg = ("Cannot use %s on a view which does not have either a "
                       "'serializer_class' or 'ordering_fields' attribute.")
                raise ImproperlyConfigured(msg % self.__class__.__name__)
            valid_fields = [
                field.source or field_name
                for field_name, field in serializer_class().fields.items()
                if not getattr(field, 'write_only', False)
            ]
        elif valid_fields == '__all__':
            # View explicitly allows filtering on any model field
            valid_fields = [field.name for field in queryset.model._meta.fields]
            valid_fields += queryset.query.aggregates.keys()

        return valid_fields

    def remove_invalid_fields(self, queryset, fields, view):
        valid_fields = self.get_valid_fields(queryset, view)
        return [term for term in fields if term.lstrip('-') in valid_fields]

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if ordering:
            return queryset.order_by(*ordering)

        return queryset

    def get_template_context(self, request, queryset, view):
        #default_tuple = self.get_default_ordering()
        #default = None if default_tuple is None else default_tuple[0]
        {
            'options': self.get_valid_fields(queryset, view),
        }

    def to_html(self, request, queryset, view):
        template = loader.get_template(self.template)
        context = Context(self.get_template_context(request, queryset, view))
        return template.render(context)


class DjangoObjectPermissionsFilter(BaseFilterBackend):
    """
    A filter backend that limits results to those where the requesting user
    has read object level permissions.
    """
    def __init__(self):
        assert guardian, 'Using DjangoObjectPermissionsFilter, but django-guardian is not installed'

    perm_format = '%(app_label)s.view_%(model_name)s'

    def filter_queryset(self, request, queryset, view):
        extra = {}
        user = request.user
        model_cls = queryset.model
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': get_model_name(model_cls)
        }
        permission = self.perm_format % kwargs
        if guardian.VERSION >= (1, 3):
            # Maintain behavior compatibility with versions prior to 1.3
            extra = {'accept_global_perms': False}
        else:
            extra = {}
        return guardian.shortcuts.get_objects_for_user(user, permission, queryset, **extra)
