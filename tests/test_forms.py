from django.test import TestCase, override_settings

from djangocms_moderation.forms import *
from djangocms_moderation.models import Workflow

from .utils import BaseDataTestCase


class SelectModerationFormTest(BaseDataTestCase):

    def test_form_init(self):
        form = SelectModerationForm(page=self.pg1)
        self.assertIn('workflow', form.fields)
        field_workflow = form.fields['workflow']
        self.assertQuerysetEqual(field_workflow.queryset, Workflow.objects.all(), transform=lambda x: x, ordered=False)
        self.assertEqual(field_workflow.initial, self.wf1)
