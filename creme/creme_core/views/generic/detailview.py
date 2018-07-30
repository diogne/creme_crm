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

from collections import defaultdict
from itertools import chain
import logging
import warnings

from django.db.models import Q
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import DetailView

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.core.imprint import imprint_manager
from creme.creme_core.gui.bricks import brick_registry
from creme.creme_core.gui.last_viewed import LastViewedItem
from creme.creme_core.models import CremeEntity, BrickDetailviewLocation


logger = logging.getLogger(__name__)


def detailview_bricks(user, entity):
    is_superuser = user.is_superuser
    role = user.role

    role_q = Q(role=None, superuser=True) if is_superuser else Q(role=role, superuser=False)
    locs = BrickDetailviewLocation.objects.filter(Q(content_type=None) |
                                                  Q(content_type=entity.entity_type)
                                                 ) \
                                          .filter(role_q | Q(role=None, superuser=False)) \
                                          .order_by('order')

    # We fallback to the default config is there is no config for this content type.
    locs = [loc for loc in locs
            # NB: useless as long as default conf cannot have a related role
            # if loc.content_type_id is not None
            if loc.superuser == is_superuser and loc.role == role
           ] or [loc for loc in locs if loc.content_type_id is not None] or locs
    loc_map = defaultdict(list)

    for loc in locs:
        brick_id = loc.brick_id

        if brick_id:  # Populate scripts can leave void brick ids
            if BrickDetailviewLocation.id_is_4_model(brick_id):
                brick_id = brick_registry.get_brick_4_object(entity).id_

            loc_map[loc.zone].append(brick_id)

    # We call the method block_registry.get_bricks() once to regroup additional queries
    bricks = {}
    model = entity.__class__
    for brick in brick_registry.get_bricks(list(chain.from_iterable(brick_ids for brick_ids in loc_map.values())),
                                           entity=entity,
                                          ):
        target_ctypes = brick.target_ctypes
        if target_ctypes and not model in target_ctypes:
            logger.warning('This brick cannot be displayed on this content type (you have a config problem): %s', brick.id_)
        else:
            bricks[brick.id_] = brick

    hat_bricks = loc_map[BrickDetailviewLocation.HAT]
    if not hat_bricks:
        hat_brick = brick_registry.get_generic_hat_brick(model)

        hat_bricks.append(hat_brick.id_)
        bricks[hat_brick.id_] = hat_brick

    return {zone_name: list(filter(None, (bricks.get(brick_id) for brick_id in loc_map[zone])))
                for zone, zone_name in BrickDetailviewLocation.ZONE_NAMES.items()
           }


def view_entity(request, object_id, model,
                template='creme_core/generics/view_entity.html',
                extra_template_dict=None):
    warnings.warn('creme_core.views.generics.detailview.view_entity() is deprecated ; '
                  'use the class-based view EntityDetail instead.',
                  DeprecationWarning
                 )

    from django.shortcuts import get_object_or_404, render

    entity = get_object_or_404(model, pk=object_id)

    user = request.user
    user.has_perm_to_view_or_die(entity)

    LastViewedItem(request, entity)
    imprint_manager.create_imprint(entity=entity, user=user)

    template_dict = {
        'object': entity,
        'bricks': detailview_bricks(user, entity),
        'bricks_reload_url': reverse('creme_core__reload_detailview_bricks', args=(entity.id,)),
    }

    if extra_template_dict is not None:
        template_dict.update(extra_template_dict)

    return render(request, template, template_dict)


class EntityDetail(DetailView):
    model = CremeEntity
    template_name = 'creme_core/generics/view_entity.html'
    pk_url_kwarg = 'entity_id'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        request.user.has_perm_to_access_or_die(self.model._meta.app_label)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        entity = self.object

        context['bricks'] = detailview_bricks(self.request.user, entity)
        context['bricks_reload_url'] = reverse('creme_core__reload_detailview_bricks', args=(entity.id,))

        return context

    def get_object(self, queryset=None):
        entity = super().get_object(queryset=queryset)

        request = self.request
        user = request.user
        user.has_perm_to_view_or_die(entity)

        LastViewedItem(request, entity)
        imprint_manager.create_imprint(entity=entity, user=user)

        return entity
