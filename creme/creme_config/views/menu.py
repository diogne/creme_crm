# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.gui.menu import ContainerEntry, menu_registry
from creme.creme_core.models import MenuConfigItem
from creme.creme_core.utils import get_from_POST_or_404
from creme.creme_core.views import generic

from ..forms import menu as menu_forms
from . import base


class Portal(generic.BricksView):
    template_name = 'creme_config/portals/menu.html'


# TODO: 409 if ContainerEntry is not registered ?
class ContainerAdding(base.ConfigModelCreation):
    form_class = menu_forms.ContainerAddingForm
    title = _('Add a container of entries')


class SpecialContainerAdding(base.ConfigModelCreation):
    form_class = menu_forms.SpecialContainerAddingForm
    title = _('Add a special container of entries')


class ContainerEdition(base.ConfigModelEdition):
    model = MenuConfigItem
    pk_url_kwarg = 'item_id'
    form_class = menu_forms.ContainerEditionForm
    title = _('Edit the container «{object}»')

    def get_queryset(self):
        return super().get_queryset().filter(entry_id=ContainerEntry.id)


class ContainerDeletion(base.ConfigDeletion):
    container_id_arg = 'id'

    menu_registry = menu_registry

    def perform_deletion(self, request):
        item_id = get_from_POST_or_404(
            request.POST, self.container_id_arg, cast=int,
        )

        item = get_object_or_404(MenuConfigItem, id=item_id)
        entries = self.menu_registry.get_entries([item])

        if not entries or entries[0].is_required:
            raise ConflictError('This is not a container which can be deleted')

        item.delete()
