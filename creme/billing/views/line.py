# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from json import loads as jsonloads
import warnings

from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from django.forms.models import modelformset_factory
from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import CremeEntity
from creme.creme_core.utils import get_ct_or_404
from creme.creme_core.views import generic, decorators

from creme import billing

from .. import constants
from ..core import BILLING_MODELS
from ..registry import lines_registry
from ..forms import line as line_forms


ProductLine = billing.get_product_line_model()
ServiceLine = billing.get_service_line_model()


def abstract_add_multiple_product_line(request, document_id,
                                       form=line_forms.ProductLineMultipleAddForm,
                                       title=_('Add one or more product to «%s»'),
                                       submit_label=_('Save the lines'),
                                      ):
    warnings.warn('billing.views.line.abstract_add_multiple_product_line() is deprecated ; '
                  'use the class-based view ProductLinesCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_to_entity(request, document_id, form, title,
                                 link_perm=True, submit_label=submit_label,
                                )


def abstract_add_multiple_service_line(request, document_id,
                                       form=line_forms.ServiceLineMultipleAddForm,
                                       title=_('Add one or more service to «%s»'),
                                       submit_label=_('Save the lines'),
                                      ):
    warnings.warn('billing.views.line.abstract_add_multiple_service_line() is deprecated ; '
                  'use the class-based view ServiceLinesCreation instead.',
                  DeprecationWarning
                 )
    return generic.add_to_entity(request, document_id, form, title,
                                 link_perm=True, submit_label=submit_label,
                                )


@login_required
@permission_required('billing')
def add_multiple_product_line(request, document_id):
    warnings.warn('billing.views.line.add_multiple_product_line() is deprecated.',
                  DeprecationWarning
                 )
    return abstract_add_multiple_product_line(request, document_id)


@login_required
@permission_required('billing')
def add_multiple_service_line(request, document_id):
    warnings.warn('billing.views.line.add_multiple_service_line() is deprecated.',
                  DeprecationWarning
                 )
    return abstract_add_multiple_service_line(request, document_id)


# TODO: LINK credentials + link-popup.html ??
class _LinesCreation(generic.RelatedToEntityFormPopup):
    # model = Line
    # form_class = line_forms._LineMultipleAddForm
    submit_label = _('Save the lines')
    entity_classes = BILLING_MODELS

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_link_or_die(entity)


class ProductLinesCreation(_LinesCreation):
    # model = ProductLine
    form_class = line_forms.ProductLineMultipleAddForm
    title = _('Add one or more product to «{entity}»')


class ServiceLinesCreation(_LinesCreation):
    # model = ServiceLine
    form_class = line_forms.ServiceLineMultipleAddForm
    title = _('Add one or more service to «{entity}»')


@login_required
@permission_required('billing')
def listview_product_line(request):
    return generic.list_view(request, ProductLine, show_actions=False)


@login_required
@permission_required('billing')
def listview_service_line(request):
    return generic.list_view(request, ServiceLine, show_actions=False)


class AddingToCatalog(generic.RelatedToEntityFormPopup):
    # model = ...
    form_class = line_forms.AddToCatalogForm
    permissions = 'billing'
    title = _('Add this on the fly item to your catalog')
    submit_label = _('Add to the catalog')
    entity_id_url_kwarg = 'line_id'
    entity_form_kwarg = 'line'
    lines_registry = lines_registry

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)  # TODO: test

    def get_form_kwargs(self):
        kwargs = super(AddingToCatalog, self).get_form_kwargs()
        kwargs['related_item_class'] = self.get_item_class()

        return kwargs

    def get_item_class(self):
        line = self.get_related_entity()

        if not any(isinstance(line, c) for c in self.lines_registry):
            raise Http404('This entity is not a billing line')  # TODO: ConflictError ??

        cls = line.related_item_class()
        self.request.user.has_perm_to_create_or_die(cls)

        return cls


LINE_FORMSET_PREFIX = {
    ProductLine: 'product_line_formset',
    ServiceLine: 'service_line_formset',
}


@decorators.POST_only
@login_required
@permission_required('billing')
@atomic
def multi_save_lines(request, document_id):
    get_for_ct = ContentType.objects.get_for_model
    b_entity = get_object_or_404(
        CremeEntity.objects.select_for_update(),
        pk=document_id,
        entity_type__in=[get_for_ct(c) for c in BILLING_MODELS],
    ).get_real_entity()

    user = request.user
    user.has_perm_to_change_or_die(b_entity)

    formset_to_save = []
    errors = []

    class _LineForm(line_forms.LineEditForm):
        def __init__(self, *args, **kwargs):
            self.empty_permitted = False
            super().__init__(user=user, related_document=b_entity, *args, **kwargs)

    # Only modified formsets land here
    for line_ct_id, data in request.POST.items():
        line_model = get_ct_or_404(line_ct_id).model_class()

        prefix = LINE_FORMSET_PREFIX.get(line_model)
        if prefix is None:
            raise ConflictError('Invalid model (not a line ?!)')

        qs = line_model.objects.filter(relations__object_entity=b_entity.id,
                                       relations__type=constants.REL_OBJ_HAS_LINE,
                                      )

        lineformset_class = modelformset_factory(line_model, form=_LineForm, extra=0, can_delete=True)
        lineformset = lineformset_class(jsonloads(data), prefix=prefix, queryset=qs)

        if lineformset.is_valid():
            formset_to_save.append(lineformset)
        else:
            get_field = line_model._meta.get_field

            for form in lineformset:
                if form.errors:
                    instance = form.instance
                    item = None

                    if instance.pk:
                        # We retrieve the line again because the field 'on_the_fly_item' may have been cleaned
                        # TODO: avoid this query (API for field modifications -- see HistoryLine)
                        item = line_model.objects.get(pk=instance.pk).on_the_fly_item or instance.related_item

                    errors.append({'item':     item,
                                   'instance': instance,
                                   'errors':   [(None if field == '__all__' else get_field(field),
                                                 msg,
                                                ) for field, msg in form.errors.items()
                                               ],
                                  }
                                 )

    if errors:
        return render(request, 'billing/frags/lines-errors.html', context={'errors': errors}, status=409)

    # Save all formset now that we haven't detect any errors
    for formset in formset_to_save:
        formset.save()

    return HttpResponse()
