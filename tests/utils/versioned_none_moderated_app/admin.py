from django.contrib import admin

from .models import NoneModeratedPoll, NoneModeratedPollContent


@admin.register(NoneModeratedPollContent)
class NoneModeratedPollContentAdmin(admin.ModelAdmin):
    pass


@admin.register(NoneModeratedPoll)
class NoneModeratedPollAdmin(admin.ModelAdmin):
    pass
