# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2012  Hybird
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

from django.db import models
from django.db.models.fields.related import ForeignKey
from django.db.models.fields import FieldDoesNotExist, DateTimeField, DateField
from django.forms.util import ValidationError
from django.forms.fields import ChoiceField, BooleanField, CharField
from django.forms.widgets import Select, CheckboxInput
from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.models.relation import RelationType
from creme.creme_core.forms.base import CremeEntityForm
from creme.creme_core.forms.widgets import DependentSelect, Label
from creme.creme_core.forms.fields import AjaxChoiceField
from creme.creme_core.utils.meta import ModelFieldEnumerator #get_flds_with_fk_flds

from ..report_aggregation_registry import field_aggregation_registry
from ..models.graph import ReportGraph, RGT_FK, RGT_RANGE, RGT_RELATION


AUTHORIZED_AGGREGATE_FIELDS = field_aggregation_registry.authorized_fields
AUTHORIZED_ABSCISSA_TYPES = (models.DateField, models.DateTimeField, models.ForeignKey)


class ReportGraphAddForm(CremeEntityForm):
    report_lbl        = CharField(label=_(u'Report'), widget=Label)

    aggregates        = ChoiceField(label=_(u'Ordinate aggregate'), choices=[(aggregate.name, aggregate.title) for aggregate in field_aggregation_registry.itervalues()],required=False)
    aggregates_fields = ChoiceField(label=_(u'Ordinate aggregate field'), choices=())

    abscissa_fields   = ChoiceField(label=_(u'Abscissa field'), choices=(), widget=DependentSelect(target_id='id_abscissa_group_by'))#DependentSelect is kept until *Selector widgets accept optgroup
    abscissa_group_by = AjaxChoiceField(label=_(u'Abscissa : Group by'), choices=(), widget=Select(attrs={'id': 'id_abscissa_group_by'}))

    is_count = BooleanField(label=_(u'Entities count'), help_text=_(u'Make a count instead of aggregate ?'), required=False, widget=CheckboxInput(attrs={'onchange': "creme.reports.graphs.toggleDisableOthers(this, ['#id_aggregates', '#id_aggregates_fields']);"}))

    blocks = CremeEntityForm.blocks.new(
                ('abscissa', _(u'Abscissa informations'),  ['abscissa_fields', 'abscissa_group_by', 'days']),
                ('ordinate', _(u'Ordinates informations'), ['is_count', 'aggregates', 'aggregates_fields']),
            )

    class Meta:
        model = ReportGraph
        exclude = CremeEntityForm.Meta.exclude + ('ordinate', 'abscissa', 'type', 'report')

    def __init__(self, entity, *args, **kwargs):
        super(ReportGraphAddForm, self).__init__(*args,  **kwargs)
        self.report = entity
        report_ct = entity.ct
        model = report_ct.model_class()

        fields = self.fields

        fields['report_lbl'].initial = unicode(entity)
        aggregates_fields = fields['aggregates_fields']
        aggregates        = fields['aggregates']
        abscissa_fields   = fields['abscissa_fields']

        #aggregates_fields.choices = [(f.name, unicode(f.verbose_name)) for f in get_flds_with_fk_flds(model, deep=0) if isinstance(f, AUTHORIZED_AGGREGATE_FIELDS)]
        aggregates_fields.choices = ModelFieldEnumerator(model, deep=0) \
                                        .filter((lambda f: isinstance(f, AUTHORIZED_AGGREGATE_FIELDS)), viewable=True) \
                                        .choices()
        if not aggregates_fields.choices:
             aggregates_fields.required = False
             aggregates.required = False

        abscissa_predicates   = [(rtype.id, rtype.predicate) for rtype in RelationType.get_compatible_ones(report_ct, include_internals=True).order_by('predicate')]#Relation type as abscissa
        #abscissa_model_fields   = [(f.name, unicode(f.verbose_name)) for f in get_flds_with_fk_flds(model, deep=0) if isinstance(f, AUTHORIZED_ABSCISSA_TYPES)]#One field of the model as abscissa
        #One field of the model as abscissa
        abscissa_model_fields = ModelFieldEnumerator(model, deep=0, only_leafs=False) \
                                    .filter((lambda f: isinstance(f, AUTHORIZED_ABSCISSA_TYPES)), viewable=True) \
                                    .choices()
        abscissa_model_fields.sort(key=lambda x: x[1])

        abscissa_fields.choices = ((_(u"Fields"), abscissa_model_fields), (_(u"Relations"), abscissa_predicates))
        abscissa_fields.widget.target_url = '/reports/graph/get_available_types/%s' % str(report_ct.id) #Bof

        data = self.data

        if data:
            abscissa_fields.widget.source_val = data.get('abscissa_fields')
            abscissa_fields.widget.target_val = data.get('abscissa_group_by')

        instance = self.instance
        if instance.pk is not None and not data:
            ordinate, sep, aggregate     = instance.ordinate.rpartition('__')
            fields['aggregates'].initial = aggregate
            aggregates_fields.initial    = ordinate
            abscissa_fields.initial      = instance.abscissa

            abscissa_fields.widget.source_val = instance.abscissa
            abscissa_fields.widget.target_val = instance.type

    def clean(self):
        cleaned_data = self.cleaned_data
        get_data     = cleaned_data.get
        model = self.report.ct.model_class() #TODO: want we several Report classes ?? If not, simply replace by 'Report' #Post TODO: What?? Each report target a different CT (Report of opportunity, of contacts...)

        try:
            abscissa_group_by = int(get_data('abscissa_group_by'))
        except (ValueError, TypeError):
            abscissa_group_by = None

        abscissa_fields = get_data('abscissa_fields')
        abscissa_field  = None
        aggregates_fields = get_data('aggregates_fields')
        is_count = get_data('is_count')

        def val_err():
            return ValidationError(self.fields['abscissa_group_by'].error_messages['invalid_choice'] % {'value': abscissa_fields})

        is_abscissa_group_by_is_RGT_RELATION = abscissa_group_by == RGT_RELATION #TODO: used once ??

        try:
            abscissa_field = model._meta.get_field(abscissa_fields)
        except FieldDoesNotExist:
            if not is_abscissa_group_by_is_RGT_RELATION:
                raise val_err()
            else:
                try:
                    RelationType.objects.get(pk=abscissa_fields)
                except Exception:
                    raise val_err()

        is_abscissa_group_by_is_RGT_FK = abscissa_group_by == RGT_FK

        #TODO: factorise "if is_abscissa_group_by_is_RGT_FK"
        if isinstance(abscissa_field, ForeignKey) and not is_abscissa_group_by_is_RGT_FK:
            raise val_err()
        if isinstance(abscissa_field, (DateField, DateTimeField)) and is_abscissa_group_by_is_RGT_FK:
            raise val_err()

        if abscissa_group_by == RGT_RANGE and not cleaned_data.get('days'):
            raise ValidationError(ugettext(u"You have to specify a day range if you use 'by X days'"))

        if not aggregates_fields and not is_count:
            raise ValidationError(ugettext(u"If you don't choose an ordinate field (or none available) you have to check 'Make a count instead of aggregate ?'"))

        return cleaned_data

    def save(self):
        get_data = self.cleaned_data.get

        graph =  self.instance# or ReportGraph()
        graph.user     = get_data('user')
        graph.name     = get_data('name')
        graph.report   = self.report
        graph.abscissa = get_data('abscissa_fields')

        aggregates_fields = get_data('aggregates_fields')

        if aggregates_fields:
            graph.ordinate = '%s__%s' % (aggregates_fields, get_data('aggregates'))
        else:
            graph.ordinate = u""

        graph.type     = get_data('abscissa_group_by')
        graph.is_count = get_data('is_count')
        graph.days     = get_data('days')
        graph.save()

        return graph
