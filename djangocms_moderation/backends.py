from django.utils.encoding import python_2_unicode_compatible
import uuid

def defaultWorkflowReferenceNumberBackend(self, **kwargs):
    self.reference_number = uuid.uuid4()
