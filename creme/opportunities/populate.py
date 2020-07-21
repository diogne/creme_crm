# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

import logging
from functools import partial

from django.apps import apps
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme import persons, products
from creme.creme_core import bricks as core_bricks
from creme.creme_core.core.entity_cell import (
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    ButtonMenuItem,
    CustomBrickConfigItem,
    EntityFilter,
    HeaderFilter,
    RelationType,
    SearchConfigItem,
    SettingValue,
)

from . import bricks, constants, get_opportunity_model, setting_keys
from .buttons import LinkedOpportunityButton
from .models import Origin, SalesPhase

logger = logging.getLogger(__name__)
Opportunity = get_opportunity_model()


class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons', 'activities', 'products', 'billing']  # 'creme_config'

    def populate(self):
        already_populated = RelationType.objects.filter(pk=constants.REL_SUB_TARGETS).exists()

        Contact = persons.get_contact_model()
        Organisation = persons.get_organisation_model()
        Product = products.get_product_model()
        Service = products.get_service_model()

        # ---------------------------
        create_rtype = RelationType.create
        rt_sub_targets = create_rtype(
            (
                constants.REL_SUB_TARGETS,
                _('targets the organisation/contact'),
                [Opportunity],
            ),
            (
                constants.REL_OBJ_TARGETS,
                _('targeted by the opportunity'),
                [Organisation, Contact],
            ),
            is_internal=True,
            minimal_display=(True, True),
        )[0]
        rt_obj_emit_orga = create_rtype(
            (
                constants.REL_SUB_EMIT_ORGA,
                _('has generated the opportunity'),
                [Organisation],
            ),
            (
                constants.REL_OBJ_EMIT_ORGA,
                _('has been generated by'),
                [Opportunity],
            ),
            is_internal=True,
            minimal_display=(True, True),
        )[1]
        create_rtype(
            (constants.REL_SUB_LINKED_PRODUCT, _('is linked to the opportunity'), [Product]),
            (constants.REL_OBJ_LINKED_PRODUCT, _('concerns the product'),         [Opportunity])
        )
        create_rtype(
            (constants.REL_SUB_LINKED_SERVICE, _('is linked to the opportunity'), [Service]),
            (constants.REL_OBJ_LINKED_SERVICE, _('concerns the service'),         [Opportunity]),
        )
        create_rtype(
            (constants.REL_SUB_LINKED_CONTACT, _('involves in the opportunity'),  [Contact]),
            (constants.REL_OBJ_LINKED_CONTACT, _('stages'),                       [Opportunity])),
        create_rtype(
            (constants.REL_SUB_RESPONSIBLE,    _('is responsible for'),           [Contact]),
            (constants.REL_OBJ_RESPONSIBLE,    _('has as responsible contact'),   [Opportunity]),
        )

        if apps.is_installed('creme.activities'):
            logger.info(
                'Activities app is installed'
                ' => an Opportunity can be the subject of an Activity'
            )

            from creme.activities.constants import REL_SUB_ACTIVITY_SUBJECT

            RelationType.objects.get(
                pk=REL_SUB_ACTIVITY_SUBJECT,
            ).add_subject_ctypes(Opportunity)

        if apps.is_installed('creme.billing'):
            logger.info(
                'Billing app is installed'
                ' => we create relationships between Opportunities & billing models'
            )

            from creme import billing

            Invoice    = billing.get_invoice_model()
            Quote      = billing.get_quote_model()
            SalesOrder = billing.get_sales_order_model()

            create_rtype(
                (
                    constants.REL_SUB_LINKED_SALESORDER,
                    _('is associate with the opportunity'),
                    [SalesOrder],
                ), (
                    constants.REL_OBJ_LINKED_SALESORDER,
                    _('has generated the salesorder'),
                    [Opportunity]
                ),
            )
            create_rtype(
                (
                    constants.REL_SUB_LINKED_INVOICE,
                    _('generated for the opportunity'),
                    [Invoice],
                ), (
                    constants.REL_OBJ_LINKED_INVOICE,
                    _('has resulted in the invoice'),
                    [Opportunity],
                ),
            )
            create_rtype(
                (
                    constants.REL_SUB_LINKED_QUOTE,
                    _('generated for the opportunity'),
                    [Quote],
                ), (
                    constants.REL_OBJ_LINKED_QUOTE,
                    _('has resulted in the quote'),
                    [Opportunity],
                ),
            )
            create_rtype(
                (
                    constants.REL_SUB_CURRENT_DOC,
                    _('is the current accounting document of'),
                    [SalesOrder, Invoice, Quote],
                ), (
                    constants.REL_OBJ_CURRENT_DOC,
                    _('has as current accounting document'),
                    [Opportunity],
                ),
            )

        # ---------------------------
        create_sv = SettingValue.objects.get_or_create
        create_sv(key_id=setting_keys.quote_key.id,              defaults={'value': False})
        create_sv(key_id=setting_keys.target_constraint_key.id,  defaults={'value': True})
        create_sv(key_id=setting_keys.emitter_constraint_key.id, defaults={'value': True})

        # ---------------------------
        create_efilter = partial(
            EntityFilter.objects.smart_update_or_create,
            model=Opportunity, user='admin',
        )
        build_cond = partial(
            condition_handler.RegularFieldConditionHandler.build_condition,
            model=Opportunity,
        )
        create_efilter(
            'opportunities-opportunities_won',
            name=_('Opportunities won'),
            conditions=[
                build_cond(operator=operators.EqualsOperator,
                           field_name='sales_phase__won',
                           values=[True],
                          ),
            ],
        )
        create_efilter(
            'opportunities-opportunities_lost',
            name=_('Opportunities lost'),
            conditions=[
                build_cond(operator=operators.EqualsOperator,
                           field_name='sales_phase__lost',
                           values=[True],
                          ),
            ],
        )
        create_efilter(
            'opportunities-neither_won_nor_lost_opportunities',
            name=_('Neither won nor lost opportunities'),
            conditions=[
                build_cond(
                    operator=operators.EqualsNotOperator,
                    field_name='sales_phase__won',
                    values=[True],
                ),
                build_cond(
                    operator=operators.EqualsNotOperator,
                    field_name='sales_phase__lost',
                    values=[True],
                ),
            ],
        )

        # ---------------------------
        HeaderFilter.objects.create_if_needed(
            pk=constants.DEFAULT_HFILTER_OPPORTUNITY, model=Opportunity,
            name=_('Opportunity view'),
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                EntityCellRelation(model=Opportunity, rtype=rt_sub_targets),
                (EntityCellRegularField, {'name': 'sales_phase'}),
                (EntityCellRegularField, {'name': 'estimated_sales'}),
                (EntityCellRegularField, {'name': 'made_sales'}),
                (EntityCellRegularField, {'name': 'closing_date'}),
            ],
        )

        # ---------------------------
        SearchConfigItem.objects.create_if_needed(
            Opportunity,
            ['name', 'made_sales', 'sales_phase__name', 'origin__name'],
        )

        # ---------------------------
        if not already_populated:
            create_sphase = SalesPhase.objects.create
            create_sphase(order=1, name=_('Forthcoming'))
            create_sphase(order=4, name=pgettext('opportunities-sales_phase', 'Abandoned'))
            create_sphase(order=5, name=pgettext('opportunities-sales_phase', 'Won'), won=True)
            create_sphase(order=6, name=pgettext('opportunities-sales_phase', 'Lost'), lost=True)
            create_sphase(order=3, name=_('Under negotiation'))
            create_sphase(order=2, name=_('In progress'))

            # ---------------------------
            create_origin = Origin.objects.create
            create_origin(name=pgettext('opportunities-origin', 'None'))
            create_origin(name=_('Web site'))
            create_origin(name=_('Mouth'))
            create_origin(name=_('Show'))
            create_origin(name=_('Direct email'))
            create_origin(name=_('Direct phone call'))
            create_origin(name=_('Employee'))
            create_origin(name=_('Partner'))
            create_origin(name=pgettext('opportunities-origin', 'Other'))

            # ---------------------------
            create_button = ButtonMenuItem.objects.create_if_needed
            create_button(
                pk='opportunities-linked_opp_button',  # TODO: This pk is kept for compatibility
                model=Organisation, button=LinkedOpportunityButton, order=30,
            )
            create_button(
                pk='opportunities-linked_opp_button_contact',
                model=Contact,      button=LinkedOpportunityButton, order=30
            )

            # ---------------------------
            LEFT = BrickDetailviewLocation.LEFT
            RIGHT = BrickDetailviewLocation.RIGHT

            build_cell = EntityCellRegularField.build
            cbci = CustomBrickConfigItem.objects.create(
                id='opportunities-complementary',
                name=_('Opportunity complementary information'),
                content_type=Opportunity,
                cells=[
                    build_cell(Opportunity, 'reference'),
                    build_cell(Opportunity, 'currency'),
                    build_cell(Opportunity, 'chance_to_win'),
                    build_cell(Opportunity, 'expected_closing_date'),
                    build_cell(Opportunity, 'closing_date'),
                    build_cell(Opportunity, 'origin'),
                    build_cell(Opportunity, 'first_action_date'),
                    build_cell(Opportunity, 'description'),
                ],
            )

            BrickDetailviewLocation.objects.multi_create(
                defaults={'model': Opportunity, 'zone': LEFT},
                data=[
                    {
                        'brick': bricks.OpportunityCardHatBrick, 'order': 1,
                        'zone': BrickDetailviewLocation.HAT,
                    },

                    {'brick': cbci.brick_id,                 'order':   5},
                    {'brick': core_bricks.CustomFieldsBrick, 'order':  40},
                    {'brick': bricks.BusinessManagersBrick,  'order':  60},
                    {'brick': bricks.LinkedContactsBrick,    'order':  62},
                    {'brick': bricks.LinkedProductsBrick,    'order':  64},
                    {'brick': bricks.LinkedServicesBrick,    'order':  66},
                    {'brick': core_bricks.PropertiesBrick,   'order': 450},
                    {'brick': core_bricks.RelationsBrick,    'order': 500},

                    {'brick': bricks.OppTargetBrick,    'order':  1, 'zone': RIGHT},
                    {'brick': bricks.OppTotalBrick,     'order':  2, 'zone': RIGHT},
                    {'brick': core_bricks.HistoryBrick, 'order': 20, 'zone': RIGHT},
                ],
            )

            if apps.is_installed('creme.activities'):
                logger.info(
                    'Activities app is installed'
                    ' => we use the "Future activities" & "Past activities" blocks'
                )

                from creme.activities import bricks as act_bricks

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'model': Opportunity, 'zone': RIGHT},
                    data=[
                        {'brick': act_bricks.FutureActivitiesBrick, 'order': 20},
                        {'brick': act_bricks.PastActivitiesBrick,   'order': 21},
                    ],
                )

            if apps.is_installed('creme.assistants'):
                logger.info(
                    'Assistants app is installed'
                    ' => we use the assistants blocks on detail views and portal'
                )

                from creme.assistants import bricks as a_bricks

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'model': Opportunity, 'zone': RIGHT},
                    data=[
                        {'brick': a_bricks.TodosBrick,        'order': 100},
                        {'brick': a_bricks.MemosBrick,        'order': 200},
                        {'brick': a_bricks.AlertsBrick,       'order': 300},
                        {'brick': a_bricks.UserMessagesBrick, 'order': 500},
                    ],
                )

            if apps.is_installed('creme.documents'):
                # logger.info('Documents app is installed
                # => we use the documents block on detail view')

                from creme.documents.bricks import LinkedDocsBrick

                BrickDetailviewLocation.objects.create_if_needed(
                    brick=LinkedDocsBrick, order=600, zone=RIGHT,
                    model=Opportunity,
                )

            if apps.is_installed('creme.billing'):
                logger.info(
                    'Billing app is installed'
                    ' => we use the billing blocks on detail view'
                )

                BrickDetailviewLocation.objects.multi_create(
                    defaults={'model': Opportunity, 'zone': LEFT},
                    data=[
                        {'brick': bricks.QuotesBrick,      'order': 70},
                        {'brick': bricks.SalesOrdersBrick, 'order': 72},
                        {'brick': bricks.InvoicesBrick,    'order': 74},
                    ],
                )

            if apps.is_installed('creme.emails'):
                logger.info(
                    'Emails app is installed'
                    ' => we use the emails blocks on detail view'
                )

                from creme.emails.bricks import MailsHistoryBrick

                BrickDetailviewLocation.objects.create_if_needed(
                    brick=MailsHistoryBrick, order=600, zone=RIGHT,
                    model=Opportunity,
                )

            BrickDetailviewLocation.objects.create_if_needed(
                brick=bricks.TargettingOpportunitiesBrick, order=16, zone=RIGHT,
                model=Organisation,
            )

            # ---------------------------
            if apps.is_installed('creme.reports'):
                logger.info(
                    'Reports app is installed'
                    ' => we create an Opportunity report, with 2 graphs, and related blocks'
                )
                self.create_report_n_graphes(rt_obj_emit_orga)

    def create_report_n_graphes(self, rt_obj_emit_orga):
        "Create the report 'Opportunities' and 2 ReportGraphs."
        from django.contrib.auth import get_user_model

        from creme.creme_core.utils.meta import FieldInfo

        from creme import reports
        from creme.reports import constants as rep_constants
        from creme.reports.core.graph.fetcher import SimpleGraphFetcher
        from creme.reports.models import Field

        admin = get_user_model().objects.get_admin()

        if reports.report_model_is_custom():
            logger.info('Report model is custom => no Opportunity report is created.')
            return

        # Create the report ----------------------------------------------------
        report = reports.get_report_model().objects.create(
            name=_('Opportunities'),
            user=admin,
            ct=Opportunity,
        )

        # TODO: helper method(s) (see EntityFilterCondition)
        create_field = partial(Field.objects.create, report=report, type=rep_constants.RFT_FIELD)
        create_field(name='name',              order=1)
        create_field(name='estimated_sales',   order=2)
        create_field(name='made_sales',        order=3)
        create_field(name='sales_phase__name', order=4)
        create_field(name=rt_obj_emit_orga.id, order=5, type=rep_constants.RFT_RELATION)

        # Create 2 graphs ------------------------------------------------------
        if reports.rgraph_model_is_custom():
            logger.info(
                'ReportGraph model is custom'
                ' => no Opportunity report-graph is created.'
            )
            return

        sales_cell = EntityCellRegularField.build(Opportunity, 'estimated_sales')
        if sales_cell is None:
            logger.warning(
                'Opportunity seems not having a field "estimated_sales"'
                ' => no ReportGraph created.'
            )
            return

        # TODO: helper method (range only on DateFields etc...)
        create_graph = partial(
            reports.get_rgraph_model().objects.create,
            linked_report=report, user=admin,
            # is_count=False, ordinate='estimated_sales__sum',
            ordinate_type=rep_constants.RGA_SUM,
            ordinate_cell_key=sales_cell.key,
        )
        esales_vname = FieldInfo(Opportunity, 'estimated_sales').verbose_name
        rgraph1 = create_graph(
            name=_('Sum {estimated_sales} / {sales_phase}').format(
                estimated_sales=esales_vname,
                sales_phase=FieldInfo(Opportunity, 'sales_phase').verbose_name,
            ),
            # abscissa='sales_phase', type=rep_constants.RGT_FK,
            abscissa_type=rep_constants.RGT_FK,
            abscissa_cell_value='sales_phase',
        )
        rgraph2 = create_graph(
            name=_('Sum {estimated_sales} / Quarter (90 days on {closing_date})').format(
                estimated_sales=esales_vname,
                closing_date=FieldInfo(Opportunity, 'closing_date').verbose_name,
            ),
            # abscissa='closing_date', type=rep_constants.RGT_RANGE, days=90,
            abscissa_type=rep_constants.RGT_RANGE,
            abscissa_cell_value='closing_date',
            abscissa_parameter='90',
        )

        # Create 2 instance block items for the 2 graphs -----------------------
        # brick_id1 = rgraph1.create_instance_brick_config_item().brick_id
        # brick_id2 = rgraph2.create_instance_brick_config_item().brick_id
        brick_id1 = SimpleGraphFetcher(rgraph1).create_brick_config_item().brick_id
        brick_id2 = SimpleGraphFetcher(rgraph2).create_brick_config_item().brick_id

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            zone=BrickDetailviewLocation.RIGHT, model=Opportunity,
        )
        create_bdl(brick=brick_id1, order=4)
        create_bdl(brick=brick_id2, order=6)

        create_hbl = BrickHomeLocation.objects.create
        create_hbl(brick_id=brick_id1, order=5)
        create_hbl(brick_id=brick_id2, order=6)
