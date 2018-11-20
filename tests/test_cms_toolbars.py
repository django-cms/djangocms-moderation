import mock

from django.contrib.auth.models import Permission, User
from django.test.client import RequestFactory
from django.urls import reverse

from cms.middleware.toolbar import ToolbarMiddleware
from cms.toolbar.toolbar import CMSToolbar

from djangocms_versioning.test_utils.factories import (
    PageVersionFactory,
    UserFactory,
)

from djangocms_moderation import constants
from djangocms_moderation.cms_toolbars import ModerationToolbar
from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequest,
    Role,
    Workflow,
)

from .utils.base import BaseTestCase


class TestCMSToolbars(BaseTestCase):
    def _get_page_request(self, page, user):
        request = RequestFactory().get('/')
        request.session = {}
        request.user = user
        request.current_page = page
        mid = ToolbarMiddleware()
        mid.process_request(request)
        if hasattr(request, 'toolbar'):
            request.toolbar.populate()
        return request

    def _get_toolbar(self, content_obj, user=None, **kwargs):
        """Helper method to set up the toolbar
        """
        if not user:
            user = UserFactory(is_staff=True)
        request = self._get_page_request(
            page=content_obj.page if content_obj else None, user=user
        )
        cms_toolbar = CMSToolbar(request)
        toolbar = ModerationToolbar(
            cms_toolbar.request, toolbar=cms_toolbar, is_current_app=True, app_path='/')
        toolbar.toolbar.set_object(content_obj)
        if kwargs.get('edit_mode', False):
            toolbar.toolbar.edit_mode_active = True
            toolbar.toolbar.content_mode_active = False
            toolbar.toolbar.structure_mode_active = False
        elif kwargs.get('structure_mode', False):
            toolbar.toolbar.edit_mode_active = False
            toolbar.toolbar.content_mode_active = False
            toolbar.toolbar.structure_mode_active = True
        elif kwargs.get('preview_mode', False):
            toolbar.toolbar.edit_mode_active = False
            toolbar.toolbar.content_mode_active = True
            toolbar.toolbar.structure_mode_active = False
        return toolbar

    def _find_buttons(self, callable_or_name, toolbar):
        found = []

        if callable(callable_or_name):
            func = callable_or_name
        else:
            def func(button):
                return button.name == callable_or_name

        for button_list in toolbar.get_right_items():
            found = found + [button for button in button_list.buttons if func(button)]
        return found

    def _button_exists(self, callable_or_name, toolbar):
        found = self._find_buttons(callable_or_name, toolbar)
        return bool(len(found))

    def _find_menu_item(self, name, toolbar):
        for left_item in toolbar.get_left_items():
            for menu_item in left_item.items:
                try:
                    if menu_item.name == name:
                        return menu_item
                # Break item has no attribute `name`
                except AttributeError:
                    pass

    def test_submit_for_moderation_not_version_locked(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory(created_by=self.user)
        toolbar = self._get_toolbar(version.content, user=self.user, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('Submit for moderation', toolbar.toolbar))

    def test_submit_for_moderation_version_locked(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory(created_by=self.user2)
        # Same user to version author is logged in
        toolbar = self._get_toolbar(version.content, user=self.user2, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        # Submit for moderation button has been added
        self.assertTrue(self._button_exists('Submit for moderation', toolbar.toolbar))

        # Different user to version author is logged in
        toolbar = self._get_toolbar(version.content, user=self.user, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        # No Submit for moderation button has been added
        self.assertFalse(self._button_exists('Submit for moderation', toolbar.toolbar))

    def test_page_in_collection_collection(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory()
        self.collection1.add_version(version=version)

        toolbar = self._get_toolbar(version.content, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists(
            'In collection "{} ({})"'.format(
                self.collection1.name, self.collection1.id
            ),
            toolbar.toolbar)
        )

    def test_page_in_collection_moderating(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory()
        self.collection1.add_version(version=version)
        self.collection1.status = constants.IN_REVIEW
        self.collection1.save()

        toolbar = self._get_toolbar(version.content, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists(
            'In moderation "{} ({})"'.format(
                self.collection1.name, self.collection1.id
            ),
            toolbar.toolbar)
        )

    def test_add_edit_button_with_version_lock(self):
        """
        Version lock is in the test requirements, lets make sure it still works
        with moderation
        """
        ModerationRequest.objects.all().delete()
        # Version created with the same user as toolbar user
        version = PageVersionFactory(created_by=self.user)
        toolbar = self._get_toolbar(version.content, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('Edit', toolbar.toolbar))
        # Edit button should be clickable
        button = self._find_buttons('Edit', toolbar.toolbar)
        self.assertFalse(button[0].disabled)

        # Now version user is different to toolbar user
        version = PageVersionFactory(created_by=self.user2)
        toolbar = self._get_toolbar(version.content, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists(
            lambda button: button.name.endswith('Edit'),
            toolbar.toolbar))
        # Edit button should not be clickable
        button = self._find_buttons(
            lambda button: button.name.endswith('Edit'),
            toolbar.toolbar)
        self.assertTrue(button[0].disabled)

    def test_add_edit_button(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory(created_by=self.user)
        toolbar = self._get_toolbar(version.content, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()

        # We can see the Edit button, as the version hasn't been submitted
        # to the moderation (collection) yet
        self.assertTrue(self._button_exists('Edit', toolbar.toolbar))
        button = self._find_buttons('Edit', toolbar.toolbar)
        self.assertFalse(button[0].disabled)

        # Lets add the version to moderation, the Edit should no longer be
        # clickable
        self.collection1.add_version(version=version)

        # refresh the toolbar
        toolbar = self._get_toolbar(version.content, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('Edit', toolbar.toolbar))
        button = self._find_buttons('Edit', toolbar.toolbar)
        self.assertTrue(button[0].disabled)

    def test_add_edit_button_without_toolbar_object(self):
        ModerationRequest.objects.all().delete()
        toolbar = self._get_toolbar(None)
        toolbar.populate()
        toolbar.post_template_populate()
        # We shouldn't see Edit button when there is no toolbar object set.
        # Some of the custom views in some apps dont have toolbar.obj
        self.assertFalse(self._button_exists('Edit', toolbar.toolbar))

    @mock.patch('djangocms_moderation.cms_toolbars.helpers.is_registered_for_moderation')
    def test_publish_buttons_when_unregistered(self, mock_is_registered_for_moderation):
        mock_is_registered_for_moderation.return_value = False
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory()
        toolbar = self._get_toolbar(version.content, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('Publish', toolbar.toolbar))

    @mock.patch('djangocms_moderation.cms_toolbars.helpers.is_registered_for_moderation')
    def test_add_edit_buttons_when_unregistered(self, mock_is_registered_for_moderation):
        mock_is_registered_for_moderation.return_value = False
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory(created_by=self.user)
        toolbar = self._get_toolbar(version.content, preview_mode=True, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('Edit', toolbar.toolbar))

    def test_add_manage_collection_item_to_moderation_menu(self):
        version = PageVersionFactory(created_by=self.user)
        toolbar = self._get_toolbar(version.content, preview_mode=True, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()
        cms_toolbar = toolbar.toolbar
        manage_collection_item = self._find_menu_item('Moderation collections...', cms_toolbar)
        self.assertIsNotNone(manage_collection_item)

        collection_list_url = reverse('admin:djangocms_moderation_moderationcollection_changelist')
        collection_list_url += "?author__id__exact=%s" % self.user.pk
        self.assertTrue(manage_collection_item.url, collection_list_url)

    def test_moderation_collection_changelist_reviewer_filter(self):

        reviewer = User.objects.create_user(
            username='test_reviewer',
            email='test_reviewer@test.com',
            password='test_reviewer',
            is_staff=True
        )

        # add reviewer permissions
        perms = [
            "change_moderationcollection",
            "change_moderationrequest",
            "change_moderationrequestaction",
            "add_collectioncomment",
            "change_collectioncomment",
            "use_structure",
            "view_page"
        ]

        for perm in perms:
            permObj = Permission.objects.get(codename=perm)
            reviewer.user_permissions.add(
                permObj
            )

        moderator = User.objects.create_user(
            username='test_non_reviewer', email='test_non_reviewer@test.com',
            password='test_non_reviewer', is_staff=True, is_superuser=True)

        role = Role.objects.create(name='Role Review', user=reviewer,)
        pg = PageVersionFactory()
        wf = Workflow.objects.create(name='Workflow Review Test',)
        collection = ModerationCollection.objects.create(
            author=moderator, name='Collection Admin Actions Review', workflow=wf, status=constants.IN_REVIEW
        )

        mr = ModerationRequest.objects.create(
            version=pg, language='en',  collection=collection,
            is_active=True, author=collection.author,)

        wfst = wf.steps.create(role=role, is_required=True, order=1,)

        # this moderation request is approved
        mr.actions.create(to_user=reviewer, by_user=moderator, action=constants.ACTION_STARTED,)
        mr.actions.create(
            by_user=moderator,
            to_user=reviewer,
            action=constants.ACTION_APPROVED,
            step_approved=wfst,
        )

        # test that the moderation url in the cms_toolbar has the correct filtered URL
        url = reverse('admin:djangocms_moderation_moderationcollection_changelist')
        with self.login_user_context(moderator):
            response = self.client.get(url)
            toolbar = self._get_toolbar(pg.content, preview_mode=True, user=moderator)
            toolbar.populate()
            toolbar.post_template_populate()
            manage_collection_item = self._find_menu_item('Moderation collections...', toolbar.toolbar)
            self.assertEqual(
                manage_collection_item.url,
                '/en/admin/djangocms_moderation/moderationcollection/?moderator=' + str(moderator.pk)
            )
        with self.login_user_context(reviewer):
            response = self.client.get(url)
            toolbar = self._get_toolbar(pg.content, preview_mode=True, user=reviewer)
            toolbar.populate()
            toolbar.post_template_populate()
            manage_collection_item = self._find_menu_item('Moderation collections...', toolbar.toolbar)
            self.assertEqual(
                manage_collection_item.url,
                '/en/admin/djangocms_moderation/moderationcollection/?reviewer=' + str(reviewer.pk)
            )
