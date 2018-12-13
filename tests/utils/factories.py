import factory

from djangocms_text_ckeditor.models import Text

from djangocms_versioning.test_utils.factories import (
    get_plugin_language,
    get_plugin_position,
    PlaceholderFactory,
)

from factory.fuzzy import FuzzyChoice


class ModeratedPluginFactory(factory.django.DjangoModelFactory):
    language = factory.LazyAttribute(get_plugin_language)
    placeholder = factory.SubFactory(PlaceholderFactory)
    parent = None
    position = factory.LazyAttribute(get_plugin_position)
    plugin_type = 'ModeratedPlugin'
    body = factory.fuzzy.FuzzyText(length=50)

    class Meta:
        model = Text
