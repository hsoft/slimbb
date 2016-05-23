import json

from django.db.models import OneToOneField
try:
    from django.db.models.fields.related_descriptors import ReverseOneToOneDescriptor
except ImportError:
    from django.db.models.fields.related import SingleRelatedObjectDescriptor as ReverseOneToOneDescriptor
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import six


class AutoReverseOneToOneDescriptor(ReverseOneToOneDescriptor):
    def __get__(self, instance, instance_type=None):
        model = self.related.related_model

        try:
            return super(AutoReverseOneToOneDescriptor, self).__get__(instance, instance_type)
        except model.DoesNotExist:
            obj = model(**{self.related.field.name: instance})
            obj.save()
            return (super(AutoReverseOneToOneDescriptor, self).__get__(instance, instance_type))


class AutoOneToOneField(OneToOneField):
    """
    OneToOneField creates dependent object on first request from parent object
    if dependent oject has not created yet.
    """

    def contribute_to_related_class(self, cls, related):
        setattr(cls, related.get_accessor_name(), AutoReverseOneToOneDescriptor(related))


class JSONField(models.TextField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.
    Django snippet #1478
    """

    def from_db_value(self, value, *args):
        if value == "":
            return None

        try:
            if isinstance(value, six.string_types):
                return json.loads(value)
        except ValueError:
            pass
        return None

    def get_prep_value(self, value):
        if value == "":
            return None
        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)
            return value
