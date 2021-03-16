# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from .auth import SUPERUSER_PERM
from .gui import menu
from .models import CremeEntity, MenuConfigItem
from .utils.collections import FluentList


class HomeEntry(menu.URLEntry):
    id = 'creme_core-home'
    label = _('Home')
    url_name = 'creme_core__home'


class JobsEntry(menu.URLEntry):
    id = 'creme_core-jobs'
    label = _('Jobs')
    url_name = 'creme_core__jobs'
    permissions = SUPERUSER_PERM


class LogoutEntry(menu.URLEntry):
    id = 'creme_core-logout'
    label = _('Log out')
    url_name = 'creme_logout'


class TrashEntry(menu.URLEntry):
    """Menu entry rendering as a link to the Creme trash."""
    id = 'creme_core-trash'
    label = _('Trash')

    url_name = 'creme_core__trash'

    def render(self, context):
        count = CremeEntity.objects.filter(is_deleted=True).count()

        return format_html(
            '<a href="{url}">'
            '{label} '
            '<span class="ui-creme-navigation-punctuation">(</span>'
            '{count}'
            '<span class="ui-creme-navigation-punctuation">)</span>'
            '</a>',
            url=self.url,
            label=_('Trash'),
            count=ngettext(
                '{count} entity',
                '{count} entities',
                count,
            ).format(count=count),
        )


class CremeEntry(menu.ContainerEntry):
    id = 'creme_core-creme'
    label = 'Creme'
    is_required = True

    child_classes = FluentList([
        HomeEntry,
        TrashEntry,
        # TODO: User group
        # TODO: my_page
        # TODO: my_jobs
        # TODO: separator
        LogoutEntry,
    ])

    def __init__(self, config_item=None, children=()):
        assert not children

        super().__init__(
            config_item=config_item,
            children=(
                cls(config_item=MenuConfigItem(entry_id=cls.id))
                for cls in self.child_classes
            ),
        )


class RecentEntitiesEntry(menu.MenuEntry):
    id = 'creme_core-recent_entities'
    label = _('Recent entities')
    level = 0

    def __init__(self, config_item=None, children=()):
        assert not children
        super().__init__(config_item=config_item, children=children)

    def render(self, context):
        from .gui.last_viewed import LastViewedItem

        lv_items = LastViewedItem.get_all(context['request'])

        if lv_items:
            li_tags = format_html_join(
                '', '<li><a href="{}">{}</a></li>',
                ((lvi.url, lvi.name) for lvi in lv_items)
            )
        else:
            li_tags = format_html(
                '<li><span class="ui-creme-navigation-text-entry">{}</span></li>',
                gettext('No recently visited entity'),
            )

        return format_html(
            '{label}<ul>{li_tags}</ul>',
            label=self.render_label(context),
            li_tags=li_tags,
        )
