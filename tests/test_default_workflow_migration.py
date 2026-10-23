from copy import deepcopy
from importlib import import_module

from django.db import IntegrityError, connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature


@override_settings(MIGRATION_MODULES={})
class DefaultWorkflowMigrationTest(TransactionTestCase):
    def setUp(self):
        previous_state = MigrationLoader(connection).project_state([
            ("djangocms_moderation", "0022_alter_moderationcollection_options"),
        ])
        workflow_state = previous_state.models[("djangocms_moderation", "workflow")].clone()
        # Exercise the real migration on a separate historical Workflow table.
        workflow_state.options["db_table"] = "test_default_workflow_migration"
        self.state = ProjectState()
        self.state.add_model(workflow_state)
        self.Workflow = self.state.apps.get_model("djangocms_moderation", "Workflow")
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(self.Workflow)
        self.addCleanup(self.drop_workflow_table)

    def drop_workflow_table(self):
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(self.Workflow)

    def migrate(self):
        migration = deepcopy(import_module(
            "djangocms_moderation.migrations.0023_workflow_single_default"
        ).Migration("0023_workflow_single_default", "djangocms_moderation"))
        # Index names are shared across tables on SQLite and PostgreSQL.
        migration.operations[1].constraint.name = "test_one_default_workflow"
        with connection.schema_editor() as schema_editor:
            self.state = migration.apply(self.state, schema_editor)

    @skipUnlessDBFeature("supports_partial_indexes")
    def test_duplicate_defaults_are_normalized_before_constraint_is_added(self):
        last = self.Workflow.objects.create(name="Z workflow", is_default=True)
        first = self.Workflow.objects.create(name="A workflow", is_default=True)
        ordinary = self.Workflow.objects.create(name="B workflow", is_default=False)

        self.migrate()

        self.assertEqual(self.Workflow.objects.filter(is_default=True).get().pk, first.pk)
        self.assertEqual(
            set(self.Workflow.objects.filter(is_default=False).values_list("pk", flat=True)),
            {last.pk, ordinary.pk},
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.Workflow.objects.create(name="Another default", is_default=True)

    def test_no_default_is_preserved(self):
        self.Workflow.objects.create(name="Ordinary workflow", is_default=False)

        self.migrate()

        self.assertFalse(self.Workflow.objects.filter(is_default=True).exists())
        self.assertEqual(self.Workflow.objects.count(), 1)

    def test_single_default_is_preserved(self):
        workflow = self.Workflow.objects.create(name="Default workflow", is_default=True)

        self.migrate()

        self.assertEqual(self.Workflow.objects.filter(is_default=True).get().pk, workflow.pk)
