from django.contrib.admin.templatetags.admin_modify import *  # flake8: noqa
from django.contrib.admin.templatetags.admin_modify import (
    submit_row as original_submit_row,
)


@register.inclusion_tag('admin/submit_line.html', takes_context=True)
def submit_row(context):
    """
    Hide the row of buttons for delete and save if readonly otherwise display.
    """
    if context.get('readonly'):
        return dict()
    return original_submit_row(context)
