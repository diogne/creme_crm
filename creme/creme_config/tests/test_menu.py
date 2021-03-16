# -*- coding: utf-8 -*-
from unittest import skipIf

from django.apps import apps
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext as _

from creme.creme_core.gui.menu import ContainerEntry, menu_registry
from creme.creme_core.menu import CremeEntry, LogoutEntry, RecentEntitiesEntry
from creme.creme_core.models import FakeContact, MenuConfigItem
from creme.creme_core.tests.base import CremeTestCase, skipIfNotInstalled
from creme.creme_core.tests.fake_menu import (
    FakeContactCreationEntry,
    FakeContactsEntry,
    FakeOrganisationCreationEntry,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..bricks import MenuBrick
from ..menu import (
    BricksConfigEntry,
    ButtonsConfigEntry,
    ConfigPortalEntry,
    CremeConfigEntry,
    CurrentAppConfigEntry,
    CustomFieldsConfigEntry,
    CustomFormsConfigEntry,
    FieldsConfigEntry,
    HistoryConfigEntry,
    MySettingsEntry,
    PropertyTypesConfigEntry,
    RelationTypesConfigEntry,
    RolesConfigEntry,
    SearchConfigEntry,
    TimezoneEntry,
    UsersConfigEntry,
)
from ..views.portal import Portal

if apps.is_installed('creme.persons'):
    from creme.persons import get_contact_model
    from creme.persons.tests.base import skipIfCustomContact
else:
    def skipIfCustomContact(test_func):
        return skipIf(False, '"persons" is not installed')(test_func)


class MenuEntriesTestCase(CremeTestCase):
    def test_tz_entry(self):
        entry = TimezoneEntry()
        self.assertEqual('creme_config-timezone', entry.id)
        self.assertEqual(_("*User's timezone*"),  entry.label)

        tz = 'Europe/Madrid'
        self.assertHTMLEqual(
            '<a href="{url}">{label}</a>'.format(
                url=reverse('creme_config__user_settings'),
                label=_('Time zone: {}').format(tz),
            ),
            entry.render({
                # 'request': self.build_request(user=user),
                # 'user': user,
                'TIME_ZONE': tz,
            }),
        )

    def test_my_settings_entry(self):
        entry = MySettingsEntry()
        self.assertEqual('creme_config-my_settings',    entry.id)
        self.assertEqual(_('My settings'),              entry.label)
        self.assertEqual('creme_config__user_settings', entry.url_name)
        self.assertIsNone(entry.permissions)

    def test_portal_entry(self):
        entry = ConfigPortalEntry()
        self.assertEqual('creme_config-portal',           entry.id)
        self.assertEqual(_('General configuration'),      entry.label)
        self.assertEqual(reverse('creme_config__portal'), entry.url)
        self.assertEqual('creme_config',                  entry.permissions)

    def test_bricks_entry(self):
        entry = BricksConfigEntry()
        self.assertEqual('creme_config-bricks',           entry.id)
        self.assertEqual(_('Blocks'),                     entry.label)
        self.assertEqual(reverse('creme_config__bricks'), entry.url)
        self.assertEqual('creme_config',                  entry.permissions)

    def test_custom_fields_entry(self):
        entry = CustomFieldsConfigEntry()
        self.assertEqual('creme_config-custom_fields',           entry.id)
        self.assertEqual(_('Custom fields'),                     entry.label)
        self.assertEqual(reverse('creme_config__custom_fields'), entry.url)
        self.assertEqual('creme_config',                         entry.permissions)

    def test_fields_entry(self):
        entry = FieldsConfigEntry()
        self.assertEqual('creme_config-fields',           entry.id)
        self.assertEqual(_('Fields'),                     entry.label)
        self.assertEqual(reverse('creme_config__fields'), entry.url)
        self.assertEqual('creme_config',                  entry.permissions)

    def test_custom_forms_entry(self):
        entry = CustomFormsConfigEntry()
        self.assertEqual('creme_config-custom_forms',           entry.id)
        self.assertEqual(_('Custom forms'),                     entry.label)
        self.assertEqual(reverse('creme_config__custom_forms'), entry.url)
        self.assertEqual('creme_config',                        entry.permissions)

    def test_history_entry(self):
        entry = HistoryConfigEntry()
        self.assertEqual('creme_config-history',           entry.id)
        self.assertEqual(_('History'),                     entry.label)
        self.assertEqual(reverse('creme_config__history'), entry.url)
        self.assertEqual('creme_config',                   entry.permissions)

    def test_buttons_entry(self):
        entry = ButtonsConfigEntry()
        self.assertEqual('creme_config-buttons',           entry.id)
        self.assertEqual(_('Button menu'),                 entry.label)
        self.assertEqual(reverse('creme_config__buttons'), entry.url)
        self.assertEqual('creme_config',                   entry.permissions)

    def test_search_entry(self):
        entry = SearchConfigEntry()
        self.assertEqual('creme_config-search',           entry.id)
        self.assertEqual(_('Search'),                     entry.label)
        self.assertEqual(reverse('creme_config__search'), entry.url)
        self.assertEqual('creme_config',                  entry.permissions)

    def test_roles_entry(self):
        entry = RolesConfigEntry()
        self.assertEqual('creme_config-roles',           entry.id)
        self.assertEqual(_('Roles and credentials'),     entry.label)
        self.assertEqual(reverse('creme_config__roles'), entry.url)
        self.assertEqual('creme_config',                 entry.permissions)

    def test_property_types_entry(self):
        entry = PropertyTypesConfigEntry()
        self.assertEqual('creme_config-property_types',   entry.id)
        self.assertEqual(_('Types of property'),          entry.label)
        self.assertEqual(reverse('creme_config__ptypes'), entry.url)
        self.assertEqual('creme_config',                  entry.permissions)

    def test_relation_types_entry(self):
        entry = RelationTypesConfigEntry()
        self.assertEqual('creme_config-relation_types',   entry.id)
        self.assertEqual(_('Types of relationship'),      entry.label)
        self.assertEqual(reverse('creme_config__rtypes'), entry.url)
        self.assertEqual('creme_config',                  entry.permissions)

    def test_users_entry(self):
        entry = UsersConfigEntry()
        self.assertEqual('creme_config-users',           entry.id)
        self.assertEqual(_('Users'),                     entry.label)
        self.assertEqual(reverse('creme_config__users'), entry.url)
        self.assertEqual('creme_config',                 entry.permissions)

    def test_current_app_entry01(self):
        user = self.login()

        entry = CurrentAppConfigEntry()
        self.assertEqual('creme_config-current_app',    entry.id)
        self.assertEqual(_("*Current app's settings*"), entry.label)

        self.assertEqual(
            '',
            entry.render({
                # 'request': self.build_request(user=user),
                'user': user,
            }),
        )

        fake_contact = FakeContact.objects.create(user=user, last_name='Doe')
        self.assertHTMLEqual(
            '<a href="{url}">{label}</a>'.format(
                url=reverse('creme_config__app_portal', args=('creme_core',)),
                label=_('Configuration of «{app}»').format(app=_('Core')),
            ),
            entry.render({
                # 'request': self.build_request(user=user),
                'user': user,
                'object': fake_contact,
            }),
        )

    @skipIfCustomContact
    def test_current_app_entry02(self):
        "Other app."
        user = self.login(is_superuser=False, admin_4_apps=('persons',))

        contact = get_contact_model().objects.create(user=user, last_name='Doe')
        expected = '<a href="{url}">{label}</a>'.format(
            url=reverse('creme_config__app_portal', args=('persons',)),
            label=_('Configuration of «{app}»').format(
                app=_('Accounts and Contacts'),
            ),
        )
        render = CurrentAppConfigEntry().render
        self.assertHTMLEqual(
            expected,
            render({'user': user, 'object': contact}),
        )

        # ---
        from creme.persons.views.contact import ContactsList
        self.assertHTMLEqual(
            expected,
            render({'user': user, 'view': ContactsList()}),
        )

    @skipIfCustomContact
    def test_current_app_entry03(self):
        "Not allowed"
        user = self.login(is_superuser=False)

        contact = get_contact_model().objects.create(user=user, last_name='Doe')
        self.assertHTMLEqual(
            '<span class="ui-creme-navigation-text-entry forbidden">{}</span>'.format(
                escape(_('Configuration of «{app}»').format(
                    app=_('Accounts and Contacts'),
                )),
            ),
            CurrentAppConfigEntry().render({
                'user': user,
                'object': contact,
            }),
        )

    @skipIfNotInstalled('creme.activities')
    def test_current_app_entry04(self):
        "View without model."
        from creme.activities.views.calendar import CalendarView

        user = self.login()

        view = CalendarView()
        self.assertFalse(hasattr(view, 'model'))
        self.assertHTMLEqual(
            '<a href="{url}">{label}</a>'.format(
                url=reverse('creme_config__app_portal', args=('activities',)),
                label=_('Configuration of «{app}»').format(
                    app=_('Activities'),
                ),
            ),
            CurrentAppConfigEntry().render({'user': user, 'view': view}),
        )

    def test_current_app_entry05(self):
        "creme_config's view."
        user = self.login()

        self.assertFalse(
            CurrentAppConfigEntry().render({'user': user, 'view': Portal()}),
        )

    def test_config_entry(self):
        user = self.login()

        entry = CremeConfigEntry()
        self.assertEqual(0, entry.level)
        self.assertTrue(entry.is_required)

        entry_id = 'creme_config-main'
        self.assertEqual(entry_id, entry.id)

        entry_label = _('Configuration')
        self.assertEqual(entry_label, entry.label)

        context = {
            'request': self.build_request(user=user),
            'user': user,
            # 'THEME_NAME': 'icecream',
        }

        render = entry.render(context)
        self.assertStartsWith(
            render,
            '<svg xmlns="http://www.w3.org/2000/svg" style="display: none;">'
        )

        ul_node = self.get_html_tree(render).find('.//ul')
        self.assertIsNotNone(ul_node)

        links = []
        for li_node in ul_node.findall('li'):
            a_node = li_node.find('a')
            # TODO: beware to current app
            # TODO: separator
            links.append((a_node.get('href'), a_node.text))

        self.assertListEqual(
            [
                (reverse('creme_config__portal'),        _('General configuration')),
                (reverse('creme_config__bricks'),        _('Blocks')),
                (reverse('creme_config__custom_fields'), _('Custom fields')),
                (reverse('creme_config__fields'),        _('Fields')),
                (reverse('creme_config__custom_forms'),  _('Custom forms')),
                (reverse('creme_config__history'),       _('History')),
                (reverse('creme_config__buttons'),       _('Button menu')),
                (reverse('creme_config__search'),        _('Search')),
                (reverse('creme_config__roles'),         _('Roles and credentials')),
                (reverse('creme_config__ptypes'),        _('Types of property')),
                (reverse('creme_config__rtypes'),        _('Types of relationship')),
                (reverse('creme_config__users'),         _('Users')),
            ],
            links,
        )

    def test_global_registry(self):
        self.assertIn(CremeConfigEntry, menu_registry.entry_classes)


class MenuConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    PORTAL_URL = reverse('creme_config__menu')
    ADD_URL = reverse('creme_config__add_container_menu_entry')
    DELETE_URL = reverse('creme_config__delete_container_menu_entry')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._items_backup = [*MenuConfigItem.objects.all()]
        MenuConfigItem.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        MenuConfigItem.objects.all().delete()

        try:
            MenuConfigItem.objects.bulk_create(cls._items_backup)
        except Exception:
            print(f'{cls.__name__}: test-data backup problem')

    def setUp(self):
        super().setUp()
        self.login()

    def _build_edit_url(self, item):
        return reverse('creme_config__edit_container_menu_entry', args=(item.id,))

    def test_portal(self):
        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'creme_config/portals/menu.html')
        self.assertTemplateUsed(response, 'creme_config/bricks/menu-config.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        # brick_node =
        self.get_brick_node(
            self.get_html_tree(response.content),
            MenuBrick.id_,
        )

    def test_add_container01(self):
        url = self.ADD_URL
        response1 = self.assertGET200(url)
        self.assertEqual(_('Add a container of entries'), response1.context['title'])

        with self.assertNoException():
            choices01 = response1.context['form'].fields['entries'].choices

        contacts_index = self.assertInChoices(
            value=FakeContactsEntry.id,
            label='Test Contacts',
            choices=choices01,
        )
        contact_creation_index = self.assertInChoices(
            value=FakeContactCreationEntry.id,
            label=_('Create a contact'),
            choices=choices01,
        )
        self.assertNotInChoices(value=ContainerEntry.id, choices=choices01)
        self.assertNotInChoices(value=CremeEntry.id,     choices=choices01)

        name01 = 'Fake Contacts'
        response2 = self.client.post(
            url,
            data={
                'name': name01,

                f'entries_check_{contacts_index}': 'on',
                f'entries_value_{contacts_index}': FakeContactsEntry.id,
                f'entries_order_{contacts_index}': 1,

                f'entries_check_{contact_creation_index}': 'on',
                f'entries_value_{contact_creation_index}': FakeContactCreationEntry.id,
                f'entries_order_{contact_creation_index}': 2,
            },
        )
        self.assertNoFormError(response2)

        items01 = [*MenuConfigItem.objects.order_by('id')]
        self.assertEqual(3, len(items01))

        container01 = items01[0]
        self.assertEqual('creme_core-container', container01.entry_id)
        self.assertEqual(name01,                 container01.name)
        self.assertEqual(0,                      container01.order)
        self.assertIsNone(container01.parent)

        sub_item11 = items01[1]
        self.assertEqual(FakeContactsEntry.id, sub_item11.entry_id)
        self.assertEqual('',                   sub_item11.name)
        self.assertEqual(0,                    sub_item11.order)
        self.assertEqual(container01.id,       sub_item11.parent_id)

        sub_item12 = items01[2]
        self.assertEqual(FakeContactCreationEntry.id, sub_item12.entry_id)
        self.assertEqual('',                          sub_item12.name)
        self.assertEqual(1,                           sub_item12.order)
        self.assertEqual(container01.id,              sub_item12.parent_id)

    def test_add_container02(self):
        "There are already containers."
        create_item = MenuConfigItem.objects.create
        creme_item = create_item(entry_id=CremeEntry.id, order=0)
        # NB: notice order is not 1 => our new container must have order=11
        container1 = create_item(entry_id=ContainerEntry.id, name='My organisations', order=10)
        sub_item11 = create_item(entry_id=FakeContactsEntry.id,        order=0, parent=container1)
        sub_item12 = create_item(entry_id=FakeContactCreationEntry.id, order=1, parent=container1)

        url = self.ADD_URL
        context = self.assertGET200(url).context

        with self.assertNoException():
            choices02 = context['form'].fields['entries'].choices

        orga_creation_index = self.assertInChoices(
            value=FakeOrganisationCreationEntry.id,
            label=_('Create an organisation'),
            choices=choices02,
        )
        self.assertNotInChoices(
            value=FakeContactsEntry.id, choices=choices02,
        )
        self.assertNotInChoices(
            value=FakeContactCreationEntry.id, choices=choices02,
        )

        name = 'Fake Organisations'
        response2 = self.client.post(
            url,
            data={
                'name': name,

                f'entries_check_{orga_creation_index}': 'on',
                f'entries_value_{orga_creation_index}': FakeOrganisationCreationEntry.id,
                f'entries_order_{orga_creation_index}': 1,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(6, MenuConfigItem.objects.count())

        items = [
            *MenuConfigItem.objects.exclude(id__in=[
                creme_item.id, container1.id, sub_item11.id, sub_item12.id,
            ]),
        ]
        self.assertEqual(2, len(items))

        with self.assertNoException():
            container2 = next(
                item for item in items if item.entry_id == 'creme_core-container'
            )
        self.assertEqual(name, container2.name)
        self.assertEqual(11,   container2.order)

        sub_item21 = next(item for item in items if item is not container2)
        self.assertEqual(FakeOrganisationCreationEntry.id, sub_item21.entry_id)
        self.assertEqual('',                               sub_item21.name)
        self.assertEqual(0,                                sub_item21.order)
        self.assertEqual(container2.id,                    sub_item21.parent_id)

    def test_add_special_container01(self):
        url = reverse('creme_config__add_special_container_menu_entry')
        response1 = self.assertGET200(url)
        self.assertEqual(_('Add a special container of entries'), response1.context['title'])

        with self.assertNoException():
            choices01 = response1.context['form'].fields['entry_id'].choices

        # TODO: complete: global config entry
        self.assertInChoices(
            value=CremeEntry.id, label=CremeEntry.label, choices=choices01,
        )
        self.assertInChoices(
            value=RecentEntitiesEntry.id, label=RecentEntitiesEntry.label,
            choices=choices01,
        )
        self.assertNotInChoices(value=ContainerEntry.id, choices=choices01)
        self.assertNotInChoices(value=LogoutEntry.id,    choices=choices01)

        entry_id = CremeEntry.id
        response2 = self.client.post(url, data={'entry_id': entry_id})
        self.assertNoFormError(response2)

        items = [*MenuConfigItem.objects.all()]
        self.assertEqual(1, len(items))

        special_item = items[0]
        self.assertEqual('creme_core-creme', special_item.entry_id)
        self.assertEqual('',                 special_item.name)
        self.assertEqual(0,                  special_item.order)
        self.assertIsNone(special_item.parent)

    def test_add_special_container02(self):
        url = reverse('creme_config__add_special_container_menu_entry')

        # Order of next container should be 21
        create_item = MenuConfigItem.objects.create
        special_item1 = create_item(entry_id=CremeEntry.id, order=10)
        container = create_item(entry_id=ContainerEntry.id, order=20)
        item = create_item(entry_id=FakeContactsEntry.id, parent=container, order=0)

        response1 = self.assertGET200(url)

        with self.assertNoException():
            choices02 = response1.context['form'].fields['entry_id'].choices

        self.assertInChoices(
            value=RecentEntitiesEntry.id, label=RecentEntitiesEntry.label,
            choices=choices02,
        )
        self.assertNotInChoices(value=CremeEntry.id, choices=choices02)

        entry_id = RecentEntitiesEntry.id
        response2 = self.client.post(url, data={'entry_id': entry_id})
        self.assertNoFormError(response2)

        self.assertEqual(4, MenuConfigItem.objects.count())
        items = [
            *MenuConfigItem.objects.exclude(
                id__in=[special_item1.id, container.id, item.id],
            ),
        ]
        self.assertEqual(1, len(items))

        special_item2 = items[0]
        self.assertEqual('creme_core-recent_entities', special_item2.entry_id)
        self.assertEqual(21, special_item2.order)

    def test_edit_container01(self):
        "New items added."
        name = 'my contacts'
        create_item = MenuConfigItem.objects.create
        container1 = create_item(entry_id=ContainerEntry.id, name='My organisations', order=0)
        container2 = create_item(entry_id=ContainerEntry.id, name=name,               order=1)
        create_item(entry_id=FakeOrganisationCreationEntry.id, order=0, parent=container1)
        sub_item21 = create_item(entry_id=FakeContactsEntry.id, order=0, parent=container2)

        url = self._build_edit_url(container2)
        context = self.assertGET200(url).context
        self.assertEqual(
            _('Edit the container «{object}»').format(object=container2.name),
            context.get('title'),
        )

        with self.assertNoException():
            form = context['form']
            entries_f = form.fields['entries']
            choices = entries_f.choices

        self.assertEqual(name, form.initial.get('name'))
        self.assertEqual([sub_item21.entry_id], entries_f.initial)

        contacts_index = self.assertInChoices(
            value=FakeContactsEntry.id,
            label='Test Contacts',
            choices=choices,
        )
        contact_creation_index = self.assertInChoices(
            value=FakeContactCreationEntry.id,
            label=_('Create a contact'),
            choices=choices,
        )
        self.assertNotInChoices(value=ContainerEntry.id,                choices=choices)
        self.assertNotInChoices(value=CremeEntry.id,                    choices=choices)
        self.assertNotInChoices(value=FakeOrganisationCreationEntry.id, choices=choices)

        edited_name = name.title()
        response2 = self.client.post(
            url,
            data={
                'name': edited_name,

                f'entries_check_{contacts_index}': 'on',
                f'entries_value_{contacts_index}': FakeContactsEntry.id,
                f'entries_order_{contacts_index}': 1,

                f'entries_check_{contact_creation_index}': 'on',
                f'entries_value_{contact_creation_index}': FakeContactCreationEntry.id,
                f'entries_order_{contact_creation_index}': 2,
            },
        )
        self.assertNoFormError(response2)

        container2 = self.refresh(container2)
        self.assertEqual(edited_name, container2.name)

        sub_item21 = self.refresh(sub_item21)
        self.assertEqual(FakeContactsEntry.id, sub_item21.entry_id)
        self.assertEqual('',                   sub_item21.name)
        self.assertEqual(0,                    sub_item21.order)
        self.assertEqual(container2.id,        sub_item21.parent_id)

        sub_item22 = self.get_object_or_fail(
            MenuConfigItem, entry_id=FakeContactCreationEntry.id,
        )
        self.assertEqual('',            sub_item22.name)
        self.assertEqual(1,             sub_item22.order)
        self.assertEqual(container2.id, sub_item22.parent_id)

    def test_edit_container02(self):
        "Some items removed, some changed."
        create_item = MenuConfigItem.objects.create
        container = create_item(entry_id=ContainerEntry.id, name='My contacts', order=0)
        sub_item1 = create_item(entry_id=FakeContactsEntry.id, order=0, parent=container)
        sub_item2 = create_item(entry_id=FakeContactCreationEntry.id, order=1, parent=container)

        url = self._build_edit_url(container)
        response1 = self.assertGET200(url)

        with self.assertNoException():
            choices = response1.context['form'].fields['entries'].choices

        contact_creation_index = self.assertInChoices(
            value=FakeContactCreationEntry.id,
            label=_('Create a contact'),
            choices=choices,
        )

        response2 = self.client.post(
            url,
            data={
                'name': container.name,

                f'entries_check_{contact_creation_index}': 'on',
                f'entries_value_{contact_creation_index}': FakeContactCreationEntry.id,
                f'entries_order_{contact_creation_index}': 1,
            },
        )
        self.assertNoFormError(response2)

        sub_item1 = self.refresh(sub_item1)
        self.assertEqual('',                          sub_item1.name)
        self.assertEqual(0,                           sub_item1.order)
        self.assertEqual(FakeContactCreationEntry.id, sub_item1.entry_id)
        self.assertEqual(container.id,                sub_item1.parent_id)

        self.assertDoesNotExist(sub_item2)

    def test_edit_container_error(self):
        create_item = MenuConfigItem.objects.create
        item01 = create_item(entry_id=CremeEntry.id, order=0)
        self.assertGET404(self._build_edit_url(item01))

        item02 = create_item(entry_id=RecentEntitiesEntry.id, order=0)
        self.assertGET404(self._build_edit_url(item02))

    def test_remove_container01(self):
        create_item = MenuConfigItem.objects.create
        container = create_item(entry_id=ContainerEntry.id, name='My contacts', order=0)
        sub_item1 = create_item(entry_id=FakeContactsEntry.id, order=0, parent=container)
        sub_item2 = create_item(entry_id=FakeContactCreationEntry.id, order=1, parent=container)

        url = self.DELETE_URL
        self.assertGET405(url)

        self.assertPOST200(url, data={'id': container.id})
        self.assertDoesNotExist(container)
        self.assertDoesNotExist(sub_item1)
        self.assertDoesNotExist(sub_item2)

    def test_remove_container02(self):
        item = MenuConfigItem.objects.create(entry_id=RecentEntitiesEntry.id, order=0)
        self.assertPOST200(self.DELETE_URL, data={'id': item.id})
        self.assertDoesNotExist(item)

    def test_remove_container_errors(self):
        create_item = MenuConfigItem.objects.create
        url = reverse('creme_config__delete_container_menu_entry')

        # Required container
        item01 = create_item(entry_id=CremeEntry.id, order=0)
        self.assertPOST409(url, data={'id': item01.id})

        # Not container
        item02 = create_item(entry_id=FakeContactsEntry.id, order=0)
        self.assertPOST409(url, data={'id': item02.id})

    # TODO: reorder containers
