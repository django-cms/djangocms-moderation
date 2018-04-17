from django.utils.encoding import python_2_unicode_compatible
import uuid

def default_workflow_reference_number_backend(self, **kwargs):
    return uuid.uuid4()
