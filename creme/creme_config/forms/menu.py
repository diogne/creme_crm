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

from django import forms
from django.db.models.aggregates import Max
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeModelForm
from creme.creme_core.forms.widgets import OrderedMultipleChoiceWidget
from creme.creme_core.gui.menu import ContainerEntry, menu_registry
from creme.creme_core.models import MenuConfigItem
from creme.creme_core.utils.unicode_collation import collator


class ContainerAddingForm(CremeModelForm):
    entries = forms.MultipleChoiceField(
        label=_('Entries'), widget=OrderedMultipleChoiceWidget,
    )

    class Meta(CremeModelForm.Meta):
        model = MenuConfigItem

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        used_entry_ids = {
            *MenuConfigItem.objects.values_list('entry_id', flat=True),
        }

        choices = [
            (entry_class.id, str(entry_class().label))
            for entry_class in menu_registry.entry_classes
            if (
                entry_class.level == 1
                and entry_class.id not in used_entry_ids
            )
        ]

        sort_key = collator.sort_key
        choices.sort(key=lambda choice: sort_key(choice[0]))

        self.fields['entries'].choices = choices

    def save(self, *args, **kwargs):
        max_order = MenuConfigItem.objects.filter(
            entry_id__in=[
                entry_class.id
                for entry_class in menu_registry.entry_classes
                if entry_class.level == 0
            ],
        ).aggregate(Max('order')).get('order__max')

        instance = self.instance
        instance.entry_id = ContainerEntry.id
        instance.order = 0 if max_order is None else max_order + 1

        super().save(*args, **kwargs)

        # TODO: if commit
        for order, entry_id in enumerate(self.cleaned_data['entries']):
            self._meta.model._default_manager.create(
                entry_id=entry_id,
                order=order,
                parent=instance,
            )

        return instance


# TODO: factorise
class SpecialContainerAddingForm(CremeModelForm):
    entry_id = forms.ChoiceField(label=_('Type of container'))

    class Meta(CremeModelForm.Meta):
        model = MenuConfigItem
        exclude = ('name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        used_entry_ids = {
            *MenuConfigItem.objects.values_list('entry_id', flat=True),
        }
        self.fields['entry_id'].choices = [
            (entry_class.id, entry_class.label)
            for entry_class in menu_registry.entry_classes
            if (
                entry_class.level == 0
                and entry_class != ContainerEntry  # TODO: add self.container_id in used_entry_ids
                and entry_class.id not in used_entry_ids
            )
        ]

    def save(self, *args, **kwargs):
        max_order = MenuConfigItem.objects.filter(
            entry_id__in=[
                entry_class.id
                for entry_class in menu_registry.entry_classes
                if entry_class.level == 0
            ],
        ).aggregate(Max('order')).get('order__max')

        instance = self.instance
        instance.order = 0 if max_order is None else max_order + 1
        instance.entry_id = self.cleaned_data['entry_id']

        return super().save(*args, **kwargs)


# TODO: factorise/merge ??
class ContainerEditionForm(CremeModelForm):
    entries = forms.MultipleChoiceField(
        label=_('Entries'), widget=OrderedMultipleChoiceWidget,
    )

    class Meta(CremeModelForm.Meta):
        model = MenuConfigItem

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._children = children = [*self.instance.children.all()]

        entries_f = self.fields['entries']
        used_entry_ids = {
            *MenuConfigItem.objects.exclude(
                id__in=[child.id for child in children],
            ).values_list('entry_id', flat=True),
        }
        choices = [
            (entry_class.id, entry_class().label)
            for entry_class in menu_registry.entry_classes
            if (
                entry_class.level == 1
                and entry_class.id not in used_entry_ids
            )
        ]
        sort_key = collator.sort_key
        choices.sort(key=lambda choice: sort_key(choice[0]))

        entries_f.choices = choices
        entries_f.initial = [child.entry_id for child in children]

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        item_model = type(self.instance)
        entry_ids = self.cleaned_data['entries']
        children = self._children
        needed = len(entry_ids)
        diff_length = needed - len(children)

        if diff_length < 0:
            items_store = children[:needed]
            item_model._default_manager.filter(
                pk__in=[child.id for child in children[needed:]],
            ).delete()
        else:
            items_store = [*children]

            if diff_length > 0:
                items_store.extend(item_model(parent=instance) for __ in range(diff_length))

        store_it = iter(items_store)

        # TODO: bulk_create
        for order, entry_id in enumerate(entry_ids):
            item = next(store_it)
            item.entry_id = entry_id
            item.order = order

            item.save()

        return instance
