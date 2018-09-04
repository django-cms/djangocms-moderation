from django.contrib import admin
from django.test.client import RequestFactory
from django.urls import reverse

from cms.api import create_page

from djangocms_moderation import conf
from djangocms_moderation import constants
from djangocms_moderation import utils
from djangocms_moderation.admin import ModerationRequestAdmin, ModerationCollectionAdmin
from djangocms_moderation.constants import ACTION_REJECTED
from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequest,
    Workflow,
)

from .utils.base import BaseTestCase


class UtilsTestCase(BaseTestCase):
    def setUp(self):
    	self.rf = RequestFactory()

    def test_extract_filter_param_from_changelist_url(self):
    	mock_request = self.rf.get('/admin/djangocms_moderation/collectioncomment/add/?_changelist_filters=collection__id__exact%3D1')
    	collection_id = utils.extract_filter_param_from_changelist_url(mock_request, '_changelist_filters', 'collection__id__exact')
    	self.assertEquals(collection_id, '1')

    	mock_request = self.rf.get('/admin/djangocms_moderation/collectioncomment/add/?_changelist_filters=collection__id__exact%3D4')
    	collection_id = utils.extract_filter_param_from_changelist_url(mock_request, '_changelist_filters', 'collection__id__exact')
    	self.assertEquals(collection_id, '4')

    	mock_request = self.rf.get('/admin/djangocms_moderation/requestcomment/add/?_changelist_filters=moderation_request__id__exact%3D1')
    	action_id = utils.extract_filter_param_from_changelist_url(mock_request, '_changelist_filters', 'moderation_request__id__exact')
    	self.assertEquals(action_id, '1')

    	mock_request = self.rf.get('/admin/djangocms_moderation/requestcomment/add/?_changelist_filters=moderation_request__id__exact%3D2')
    	action_id = utils.extract_filter_param_from_changelist_url(mock_request, '_changelist_filters', 'moderation_request__id__exact')
    	self.assertEquals(action_id, '2')
