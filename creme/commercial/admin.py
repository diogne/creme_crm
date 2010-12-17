# -*- coding: utf-8 -*-

from django.contrib import admin

from commercial.models import *


class ActAdmin(admin.ModelAdmin):
    list_display = ('name', 'expected_sales', 'cost', 'goal', 'start', 'due_date')


class ApproachAdmin(admin.ModelAdmin):
    list_display = ('title', 'ok_or_in_futur', 'description', 'creation_date')


register = admin.site.register

register(Act, ActAdmin)
register(CommercialApproach, ApproachAdmin)
