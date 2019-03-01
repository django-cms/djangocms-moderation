from django import template
from django.contrib.admin.templatetags.admin_modify import (
    submit_row as original_submit_row,
)


register = template.Library()


@register.inclusion_tag("admin/submit_line.html", takes_context=True)
def comments_submit_row(context):
    """
    Displays the row of buttons for delete and save.
    """
    if context.get("readonly"):
        return dict()
    ctx = original_submit_row(context)
    ctx.update(
        {
            "show_save_and_add_another": (
                context.get("show_save_and_add_another", True)
                and context["has_add_permission"]
                and not context["is_popup"]
                and (not context["save_as"] or context["add"])
            )
        }
    )
    return ctx
