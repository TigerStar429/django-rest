from __future__ import unicode_literals
from django.db import models
from django.test import TestCase
from rest_framework import serializers


class OneToOneTarget(models.Model):
    name = models.CharField(max_length=100)


class OneToOneSource(models.Model):
    name = models.CharField(max_length=100)
    target = models.OneToOneField(OneToOneTarget, related_name='source')


class ReverseNestedOneToOneTests(TestCase):
    def setUp(self):
        class OneToOneSourceSerializer(serializers.ModelSerializer):
            class Meta:
                model = OneToOneSource
                fields = ('id', 'name')

        class OneToOneTargetSerializer(serializers.ModelSerializer):
            source = OneToOneSourceSerializer()

            class Meta:
                model = OneToOneTarget
                fields = ('id', 'name', 'source')

        self.Serializer = OneToOneTargetSerializer

        for idx in range(1, 4):
            target = OneToOneTarget(name='target-%d' % idx)
            target.save()
            source = OneToOneSource(name='source-%d' % idx, target=target)
            source.save()

    def test_one_to_one_retrieve(self):
        queryset = OneToOneTarget.objects.all()
        serializer = self.Serializer(queryset)
        expected = [
            {'id': 1, 'name': 'target-1', 'source': {'id': 1, 'name': 'source-1'}},
            {'id': 2, 'name': 'target-2', 'source': {'id': 2, 'name': 'source-2'}},
            {'id': 3, 'name': 'target-3', 'source': {'id': 3, 'name': 'source-3'}}
        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_one_create(self):
        data = {'id': 4, 'name': 'target-4', 'source': {'id': 4, 'name': 'source-4'}}
        serializer = self.Serializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'target-4')

        # Ensure (target 4, target_source 4, source 4) are added, and
        # everything else is as expected.
        queryset = OneToOneTarget.objects.all()
        serializer = self.Serializer(queryset)
        expected = [
            {'id': 1, 'name': 'target-1', 'source': {'id': 1, 'name': 'source-1'}},
            {'id': 2, 'name': 'target-2', 'source': {'id': 2, 'name': 'source-2'}},
            {'id': 3, 'name': 'target-3', 'source': {'id': 3, 'name': 'source-3'}},
            {'id': 4, 'name': 'target-4', 'source': {'id': 4, 'name': 'source-4'}}
        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_one_create_with_invalid_data(self):
        data = {'id': 4, 'name': 'target-4', 'source': {'id': 4}}
        serializer = self.Serializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'source': [{'name': ['This field is required.']}]})

    def test_one_to_one_update(self):
        data = {'id': 3, 'name': 'target-3-updated', 'source': {'id': 3, 'name': 'source-3-updated'}}
        instance = OneToOneTarget.objects.get(pk=3)
        serializer = self.Serializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'target-3-updated')

        # Ensure (target 3, target_source 3, source 3) are updated,
        # and everything else is as expected.
        queryset = OneToOneTarget.objects.all()
        serializer = self.Serializer(queryset)
        expected = [
            {'id': 1, 'name': 'target-1', 'source': {'id': 1, 'name': 'source-1'}},
            {'id': 2, 'name': 'target-2', 'source': {'id': 2, 'name': 'source-2'}},
            {'id': 3, 'name': 'target-3-updated', 'source': {'id': 3, 'name': 'source-3-updated'}}
        ]
        self.assertEqual(serializer.data, expected)


class ForwardNestedOneToOneTests(TestCase):
    def setUp(self):
        class OneToOneTargetSerializer(serializers.ModelSerializer):
            class Meta:
                model = OneToOneTarget
                fields = ('id', 'name')

        class OneToOneSourceSerializer(serializers.ModelSerializer):
            target = OneToOneTargetSerializer()

            class Meta:
                model = OneToOneSource
                fields = ('id', 'name', 'target')

        self.Serializer = OneToOneSourceSerializer

        for idx in range(1, 4):
            target = OneToOneTarget(name='target-%d' % idx)
            target.save()
            source = OneToOneSource(name='source-%d' % idx, target=target)
            source.save()

    def test_one_to_one_retrieve(self):
        queryset = OneToOneSource.objects.all()
        serializer = self.Serializer(queryset)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': {'id': 1, 'name': 'target-1'}},
            {'id': 2, 'name': 'source-2', 'target': {'id': 2, 'name': 'target-2'}},
            {'id': 3, 'name': 'source-3', 'target': {'id': 3, 'name': 'target-3'}}
        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_one_create(self):
        data = {'id': 4, 'name': 'source-4', 'target': {'id': 4, 'name': 'target-4'}}
        serializer = self.Serializer(data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-4')

        # Ensure (target 4, target_source 4, source 4) are added, and
        # everything else is as expected.
        queryset = OneToOneSource.objects.all()
        serializer = self.Serializer(queryset)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': {'id': 1, 'name': 'target-1'}},
            {'id': 2, 'name': 'source-2', 'target': {'id': 2, 'name': 'target-2'}},
            {'id': 3, 'name': 'source-3', 'target': {'id': 3, 'name': 'target-3'}},
            {'id': 4, 'name': 'source-4', 'target': {'id': 4, 'name': 'target-4'}}
        ]
        self.assertEqual(serializer.data, expected)

    def test_one_to_one_create_with_invalid_data(self):
        data = {'id': 4, 'name': 'source-4', 'target': {'id': 4}}
        serializer = self.Serializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {'target': [{'name': ['This field is required.']}]})

    def test_one_to_one_update(self):
        data = {'id': 3, 'name': 'source-3-updated', 'target': {'id': 3, 'name': 'target-3-updated'}}
        instance = OneToOneSource.objects.get(pk=3)
        serializer = self.Serializer(instance, data=data)
        self.assertTrue(serializer.is_valid())
        obj = serializer.save()
        self.assertEqual(serializer.data, data)
        self.assertEqual(obj.name, 'source-3-updated')

        # Ensure (target 3, target_source 3, source 3) are updated,
        # and everything else is as expected.
        queryset = OneToOneSource.objects.all()
        serializer = self.Serializer(queryset)
        expected = [
            {'id': 1, 'name': 'source-1', 'target': {'id': 1, 'name': 'target-1'}},
            {'id': 2, 'name': 'source-2', 'target': {'id': 2, 'name': 'target-2'}},
            {'id': 3, 'name': 'source-3-updated', 'target': {'id': 3, 'name': 'target-3-updated'}}
        ]
        self.assertEqual(serializer.data, expected)


    # TODO: Nullable 1-1 tests
    # def test_one_to_one_delete(self):
    #     data = {'id': 3, 'name': 'target-3', 'target_source': None}
    #     instance = OneToOneTarget.objects.get(pk=3)
    #     serializer = self.Serializer(instance, data=data)
    #     self.assertTrue(serializer.is_valid())
    #     serializer.save()

    #     # Ensure (target_source 3, source 3) are deleted,
    #     # and everything else is as expected.
    #     queryset = OneToOneTarget.objects.all()
    #     serializer = self.Serializer(queryset)
    #     expected = [
    #         {'id': 1, 'name': 'target-1', 'source': {'id': 1, 'name': 'source-1'}},
    #         {'id': 2, 'name': 'target-2', 'source': {'id': 2, 'name': 'source-2'}},
    #         {'id': 3, 'name': 'target-3', 'source': None}
    #     ]
    #     self.assertEqual(serializer.data, expected)
