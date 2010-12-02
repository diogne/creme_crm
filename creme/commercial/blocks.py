# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from creme_core.gui.block import Block, QuerysetBlock, list4url

from commercial.models import CommercialApproach, MarketSegment, CommercialAsset, MarketSegmentCharm


class ApproachesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('commercial', 'approaches')
    dependencies  = (CommercialApproach,)
    order_by      = 'title'
    verbose_name  = _(u'Commercial approaches')
    template_name = 'commercial/templatetags/block_approaches.html'
    configurable  = True

    #TODO: factorise with assistants blocks (CremeEntity method ??)
    @staticmethod
    def _populate_related_real_entities(comapps, user):
        entities_ids_by_ct = defaultdict(set)

        for comapp in comapps:
            entities_ids_by_ct[comapp.entity_content_type_id].add(comapp.entity_id)

        entities_map = {}
        get_ct = ContentType.objects.get_for_id

        for ct_id, entities_ids in entities_ids_by_ct.iteritems():
            entities_map.update(get_ct(ct_id).model_class().objects.in_bulk(entities_ids))

        for comapp in comapps:
            comapp.creme_entity = entities_map[comapp.entity_id]

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, CommercialApproach.get_approaches(pk),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, pk),
                                                           ))

    def portal_display(self, context, ct_ids):
        btc = self.get_block_template_context(context,
                                              CommercialApproach.get_approaches_for_ctypes(ct_ids),
                                              update_url='/creme_core/blocks/reload/portal/%s/%s/' % (self.id_, list4url(ct_ids)),
                                             )
        self._populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)

    def home_display(self, context):
        btc = self.get_block_template_context(context, CommercialApproach.get_approaches(),
                                              update_url='/creme_core/blocks/reload/home/%s/' % self.id_,
                                             )
        self._populate_related_real_entities(btc['page'].object_list, context['request'].user)

        return self._render(btc)


class SegmentsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('commercial', 'segments')
    dependencies  = (MarketSegment,)
    order_by      = 'name'
    verbose_name  = _(u'Market segments')
    template_name = 'commercial/templatetags/block_segments.html'

    def detailview_display(self, context):
        strategy = context['object']
        return self._render(self.get_block_template_context(context, strategy.segments.all(), #TODO: cached getter ??
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, strategy.pk),
                                                           ))


class AssetsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('commercial', 'assets')
    dependencies  = (CommercialAsset,)
    order_by      = 'name'
    verbose_name  = _(u'Commercial assets')
    template_name = 'commercial/templatetags/block_assets.html'

    def detailview_display(self, context):
        strategy = context['object']
        return self._render(self.get_block_template_context(context, strategy.assets.all(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, strategy.pk),
                                                           ))

class CharmsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('commercial', 'charms')
    dependencies  = (MarketSegmentCharm,)
    order_by      = 'name'
    verbose_name  = _(u'Segment charms')
    template_name = 'commercial/templatetags/block_charms.html'

    def detailview_display(self, context):
        strategy = context['object']
        return self._render(self.get_block_template_context(context, strategy.charms.all(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, strategy.pk),
                                                           ))


class EvaluatedOrgasBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('commercial', 'evaluated_orgas')
    dependencies  = (MarketSegmentCharm,)
    order_by      = 'name'
    verbose_name  = _(u'Evaluated organisations')
    template_name = 'commercial/templatetags/block_evalorgas.html'

    def detailview_display(self, context):
        strategy = context['object']
        return self._render(self.get_block_template_context(context, strategy.evaluated_orgas.all(),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, strategy.pk),
                                                           ))

class AssetsMatrixBlock(Block):
    id_           = Block.generate_id('commercial', 'assets_matrix')
    #dependencies  = (CommercialAsset,) #useless (custom reload view....)
    verbose_name  = u'Assets / segments matrix'
    template_name = 'commercial/templatetags/block_assets_matrix.html'

    def detailview_display(self, context):
        strategy = context['strategy']
        orga = context['orga']
        return self._render(self.get_block_template_context(context,
                                                            assets=strategy.get_assets_list(),
                                                            segments=strategy.get_segments_list(),
                                                            totals=strategy.get_assets_totals(orga),
                                                            update_url='/commercial/blocks/assets_matrix/%s/%s/' % (strategy.pk, orga.pk),
                                                           ))


class CharmsMatrixBlock(Block):
    id_           = Block.generate_id('commercial', 'charms_matrix')
    #dependencies  = (MarketSegmentCharm,) #useless (custom reload view....)
    verbose_name  = u'Charms / segments matrix'
    template_name = 'commercial/templatetags/block_charms_matrix.html'

    def detailview_display(self, context):
        strategy = context['strategy']
        orga = context['orga']
        return self._render(self.get_block_template_context(context,
                                                            charms=strategy.get_charms_list(),
                                                            segments=strategy.get_segments_list(),
                                                            totals=strategy.get_charms_totals(orga),
                                                            update_url='/commercial/blocks/charms_matrix/%s/%s/' % (strategy.pk, orga.pk),
                                                           ))

class AssetsCharmsMatrixBlock(Block):
    id_           = Block.generate_id('commercial', 'assets_charms_matrix')
    #dependencies  = (CommercialAsset, MarketSegmentCharm,) #useless (custom reload view....)
    verbose_name  = u'Assets / Charms segments matrix'
    template_name = 'commercial/templatetags/block_assets_charms_matrix.html'

    def detailview_display(self, context):
        strategy = context['strategy']
        orga = context['orga']
        return self._render(self.get_block_template_context(context,
                                                            segments=strategy.get_segments_list(),
                                                            update_url='/commercial/blocks/assets_charms_matrix/%s/%s/' % (strategy.pk, orga.pk),
                                                           ))


approaches_block           = ApproachesBlock()
assets_matrix_block        = AssetsMatrixBlock()
charms_matrix_block        = CharmsMatrixBlock()
assets_charms_matrix_block = AssetsCharmsMatrixBlock()

blocks_list = (
    approaches_block,
    SegmentsBlock(),
    AssetsBlock(),
    CharmsBlock(),
    EvaluatedOrgasBlock(),
    assets_matrix_block,
    charms_matrix_block,
    assets_charms_matrix_block,
)
