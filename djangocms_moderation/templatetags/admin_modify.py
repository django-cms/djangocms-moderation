from django import template
from django.contrib.admin.templatetags.admin_modify import (
    prepopulated_fields_js as original_prepopulated_fields_js,
    submit_row as original_submit_row,
)


register = template.Library()


@register.inclusion_tag('admin/prepopulated_fields_js.html', takes_context=True)
def prepopulated_fields_js(context):
    return original_prepopulated_fields_js(context)


@register.inclusion_tag('admin/submit_line.html', takes_context=True)
def submit_row(context):
    """
    Hide the row of buttons for delete and save if readonly otherwise display.
    """
    if context.get('readonly'):
        return dict()
    return original_submit_row(context)
