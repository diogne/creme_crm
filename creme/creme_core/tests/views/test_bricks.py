# -*- coding: utf-8 -*-

from functools import partial
from json import dumps as json_dump

from django.urls import reverse

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.bricks import RelationsBrick
from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui.bricks import (
    Brick,
    BricksManager,
    InstanceBrick,
    _BrickRegistry,
    brick_registry,
)
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickState,
    CustomBrickConfigItem,
    FakeAddress,
    FakeContact,
    FakeOrganisation,
    FieldsConfig,
    InstanceBrickConfigItem,
    Relation,
    RelationBrickItem,
    RelationType,
    SetCredentials,
)

from ..base import CremeTestCase
from .base import BrickTestCaseMixin


class BrickViewTestCase(CremeTestCase, BrickTestCaseMixin):
    SET_STATE_URL = reverse('creme_core__set_brick_state')

    class TestBrick(Brick):
        verbose_name = 'Testing purpose'

        string_format_detail = '<div id={}>DETAIL</div>'.format
        string_format_home   = '<div id={}>HOME</div>'.format

        def detailview_display(self, context):
            return self.string_format_detail(self.id_)

        def home_display(self, context):
            return self.string_format_home(self.id_)

    def test_set_state01(self):
        user = self.login()
        brick_id = RelationsBrick.id_

        self.assertTrue(BrickState.objects.get_for_brick_id(brick_id=brick_id, user=user).is_open)
        self.assertFalse(BrickState.objects.all())

        self.assertPOST200(self.SET_STATE_URL, data={'id': brick_id, 'is_open': 1})
        self.assertFalse(BrickState.objects.all())

        self.assertPOST200(self.SET_STATE_URL, data={'id': brick_id, 'is_open': 0})
        self.assertEqual(1, BrickState.objects.count())

        bstate = self.get_object_or_fail(BrickState, user=user, brick_id=brick_id)
        self.assertFalse(bstate.is_open)
        self.assertTrue(bstate.show_empty_fields)

        self.assertPOST200(self.SET_STATE_URL, data={'id': brick_id})  # No data
        self.assertEqual(1, BrickState.objects.count())

        bstate = self.get_object_or_fail(BrickState, user=user, brick_id=brick_id)
        self.assertFalse(bstate.is_open)
        self.assertTrue(bstate.show_empty_fields)

    def test_set_state02(self):
        user = self.login()
        brick_id = RelationsBrick.id_

        bstate = BrickState.objects.get_for_brick_id(brick_id=brick_id, user=user)
        self.assertTrue(bstate.is_open)
        self.assertTrue(bstate.show_empty_fields)
        self.assertIsNone(bstate.pk)

        # ---
        self.assertPOST200(
            self.SET_STATE_URL,
            data={'id': brick_id, 'is_open': 1, 'show_empty_fields': 1},
        )
        self.assertFalse(BrickState.objects.all())

        # ---
        self.assertPOST200(
            self.SET_STATE_URL,
            data={'id': brick_id, 'is_open': 1, 'show_empty_fields': 0},
        )
        bstate = self.get_object_or_fail(BrickState, user=user, brick_id=brick_id)
        self.assertTrue(bstate.is_open)
        self.assertFalse(bstate.show_empty_fields)

    def test_set_state03(self):
        user = self.login()
        other_user = self.other_user

        brick_id = RelationsBrick.id_
        BrickState.objects.get_for_brick_id(brick_id=brick_id, user=other_user).save()

        self.client.post(
            self.SET_STATE_URL,
            data={'id': brick_id, 'is_open': 0, 'show_empty_fields': 0},
        )

        bstates = BrickState.objects.filter(brick_id=brick_id)
        user_bstates  = [bstate for bstate in bstates if bstate.user == user]
        other_bstates = [bstate for bstate in bstates if bstate.user == other_user]

        self.assertEqual(1, len(user_bstates))
        self.assertEqual(1, len(other_bstates))
        user_bstate = user_bstates[0]
        other_bstate = other_bstates[0]

        self.assertTrue(other_bstate.is_open)
        self.assertTrue(other_bstate.show_empty_fields)

        self.assertFalse(user_bstate.is_open)
        self.assertFalse(user_bstate.show_empty_fields)

    def test_set_state04(self):
        "Instance brick."
        # "Brick ids with |"
        user = self.login()
        casca = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')

        class ContactBrick(InstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'base_block')
            dependencies = (FakeOrganisation,)
            template_name = 'persons/bricks/itdoesnotexist.html'

            def detailview_display(self, context):
                return f'<table id="{self.id_}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'  # Useless :)

        ibci = InstanceBrickConfigItem.objects.create(
            entity=casca,
            brick_class_id=ContactBrick.id_,
        )

        brick_registry = _BrickRegistry()
        brick_registry.register_4_instance(ContactBrick)

        brick_id = ibci.brick_id

        self.assertPOST200(
            self.SET_STATE_URL,
            data={'id': brick_id, 'is_open': 1, 'show_empty_fields': 1},
        )

    def test_reload_basic01(self):
        self.login()

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic01_1')
            permission = 'persons'

        class FoobarBrick2(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic01_2')
            permission = 'persons'

        brick_registry.register(FoobarBrick1, FoobarBrick2)

        response = self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={'brick_id': [FoobarBrick1.id_, FoobarBrick2.id_, 'silly_id']},
        )
        self.assertEqual('application/json', response['Content-Type'])

        fmt = self.TestBrick.string_format_detail
        self.assertListEqual(
            [
                [FoobarBrick1.id_, fmt(FoobarBrick1.id_)],
                [FoobarBrick2.id_, fmt(FoobarBrick2.id_)],
            ],
            response.json()
        )

    def test_reload_basic02(self):
        "Do not have the credentials"
        self.login(is_superuser=False)

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic02')
            permission = 'persons'

        brick_registry.register(FoobarBrick1)

        self.assertGET403(
            reverse('creme_core__reload_bricks'), data={'brick_id': FoobarBrick1.id_},
        )

    def test_reload_basic03(self):
        "Not superuser"
        app_name = 'persons'
        self.login(is_superuser=False, allowed_apps=[app_name])

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic03')
            permission = app_name

        brick_registry.register(FoobarBrick1)

        response = self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={'brick_id': FoobarBrick1.id_}
        )
        self.assertListEqual(
            [[FoobarBrick1.id_, self.TestBrick.string_format_detail(FoobarBrick1.id_)]],
            response.json()
        )

    def test_reload_basic04(self):
        "Extra data"
        self.login()
        extra_data = [1, 2]

        received_extra_data = None

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic04')

            @self.TestBrick.reloading_info.setter
            def reloading_info(self, info):
                nonlocal received_extra_data
                received_extra_data = info

        brick_registry.register(FoobarBrick)

        response = self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={
                'brick_id': FoobarBrick.id_,
                'extra_data': json_dump({FoobarBrick.id_: extra_data}),
            },
        )
        self.assertListEqual(
            [
                [FoobarBrick.id_, self.TestBrick.string_format_detail(FoobarBrick.id_)],
            ],
            response.json()
        )

        self.assertEqual(extra_data, received_extra_data)

    def test_reload_basic05(self):
        "Invalid extra data"
        self.login()

        error = None
        received_extra_data = None

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic05')

            def detailview_display(self, context):
                nonlocal error, received_extra_data

                try:
                    received_extra_data = BricksManager.get(context).get_reloading_info(self)
                except Exception as e:
                    error = e

                return super().detailview_display(context)

        brick_registry.register(FoobarBrick)

        self.assertGET200(
            reverse('creme_core__reload_bricks'),
            data={
                'brick_id': FoobarBrick.id_,
                'extra_data': '{%s: ' % FoobarBrick.id_,
            },
        )
        self.assertIsNone(received_extra_data)
        self.assertIsNotNone(error)

    def test_reload_detailview01(self):
        user = self.login()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview01')

            contact = None

            def detailview_display(self, context):
                FoobarBrick.contact = context.get('object')
                return super().detailview_display(context)

        brick_registry.register(FoobarBrick)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={'brick_id': FoobarBrick.id_},
        )
        self.assertEqual('application/json', response['Content-Type'])
        self.assertListEqual(
            [[FoobarBrick.id_, self.TestBrick.string_format_detail(FoobarBrick.id_)]],
            response.json()
        )
        self.assertEqual(atom, FoobarBrick.contact)

    def test_reload_detailview02(self):
        "With dependencies"
        user = self.login()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview02_1')
            contact = None

            def detailview_display(self, context):
                FoobarBrick1.contact = context.get('object')
                return super().detailview_display(context)

        class FoobarBrick2(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview02_2')
            contact = None

            def detailview_display(self, context):
                FoobarBrick2.contact = context.get('object')
                return super().detailview_display(context)

        class FoobarBrick3(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview02_3')
            contact = None

            def detailview_display(self, context):
                FoobarBrick3.contact = context.get('object')
                return super().detailview_display(context)

        brick_registry.register(FoobarBrick1, FoobarBrick2, FoobarBrick3)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={'brick_id': [FoobarBrick1.id_, FoobarBrick2.id_, FoobarBrick3.id_]},
        )

        fmt = self.TestBrick.string_format_detail
        self.assertEqual(
            [
                [FoobarBrick1.id_, fmt(FoobarBrick1.id_)],
                [FoobarBrick2.id_, fmt(FoobarBrick2.id_)],
                [FoobarBrick3.id_, fmt(FoobarBrick3.id_)],
            ],
            response.json()
        )
        self.assertEqual(atom, FoobarBrick1.contact)
        self.assertEqual(atom, FoobarBrick2.contact)
        self.assertEqual(atom, FoobarBrick3.contact)

    def test_reload_detailview03(self):
        "Do not have the credentials"
        self.login(is_superuser=False)

        atom = FakeContact.objects.create(
            user=self.other_user, first_name='Atom', last_name='Tenma',
        )

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview03')

        brick_registry.register(FoobarBrick)

        self.assertGET403(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={'brick_id': FoobarBrick.id_},
        )

    def test_reload_detailview04(self):
        "Not superuser"
        self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL,
        )

        atom = FakeContact.objects.create(
            user=self.other_user, first_name='Atom', last_name='Tenma',
        )
        self.assertTrue(self.user.has_perm_to_view(atom))

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview04')

        brick_registry.register(FoobarBrick)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={'brick_id': FoobarBrick.id_},
        )
        self.assertListEqual(
            [
                [FoobarBrick.id_, self.TestBrick.string_format_detail(FoobarBrick.id_)],
            ],
            response.json()
        )

    def test_reload_detailview05(self):
        "Invalid block_id"
        user = self.login()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={'brick_id': 'test_bricks_reload_detailview05'},
        )
        self.assertEqual('application/json', response['Content-Type'])
        self.assertEqual([], response.json())

    def test_reload_detailview06(self):
        "Extra data"
        user = self.login()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')
        extra_data = [1, 2]
        received_extra_data = []  # TODO: nonlocal in Py3K

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview06')

            @self.TestBrick.reloading_info.setter
            def reloading_info(self, info):
                received_extra_data.append(info)

        brick_registry.register(FoobarBrick)

        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={
                'brick_id': FoobarBrick.id_,
                'extra_data': json_dump({FoobarBrick.id_: extra_data}),
            },
        )
        self.assertListEqual(
            [
                [FoobarBrick.id_, self.TestBrick.string_format_detail(FoobarBrick.id_)],
            ],
            response.json()
        )

        self.assertTrue(received_extra_data)
        self.assertEqual(extra_data, received_extra_data[0])

    def test_reload_home(self):
        self.login()

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_home_1')

        class FoobarBrick2(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_home_2')

        brick_registry.register(FoobarBrick1, FoobarBrick2)

        response = self.assertGET200(
            reverse('creme_core__reload_home_bricks'),
            data={'brick_id': [FoobarBrick1.id_, FoobarBrick2.id_, 'silly_id']},
        )
        self.assertEqual('application/json', response['Content-Type'])
        self.assertListEqual(
            [
                [FoobarBrick1.id_, self.TestBrick.string_format_home(FoobarBrick1.id_)],
                [FoobarBrick2.id_, self.TestBrick.string_format_home(FoobarBrick2.id_)],
            ],
            response.json()
        )

    def test_relations_brick01(self):
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')
        uran  = create_contact(first_name='Uran', last_name='Ochanomizu')

        rtype1 = RelationType.create(
            ('test-subject_son',   'is the son of'),
            ('test-object_father', 'is the father of')
        )[0]
        Relation.objects.create(
            subject_entity=atom, type=rtype1, object_entity=tenma, user=user,
        )

        rtype2 = RelationType.create(
            ('test-subject_brother', 'is the brother of'),
            ('test-object_sister',   'is the sister of')
        )[0]
        Relation.objects.create(
            subject_entity=atom, type=rtype2, object_entity=uran, user=user,
        )

        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/relations.html')

        document = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(document, RelationsBrick.id_)
        self.assertInstanceLink(brick_node, tenma)
        self.assertInstanceLink(brick_node, uran)
        self.assertEqual('{}', brick_node.attrib.get('data-brick-reloading-info'))

    def test_relations_brick02(self):
        """With A SpecificRelationBrick ; but the concerned relationship is minimal_display=False
        (so there is no RelationType to exclude)
        """
        user = self.login()
        rbrick_id = RelationsBrick.id_

        rtype1 = RelationType.create(
            ('test-subject_son',   'is the son of'),
            ('test-object_father', 'is the father of')
        )[0]
        rtype2 = RelationType.create(
            ('test-subject_brother', 'is the brother of'),
            ('test-object_sister',   'is the sister of')
        )[0]
        rbi = RelationBrickItem.objects.create_if_needed(rtype1)

        BrickDetailviewLocation.objects.create_for_model_brick(
            order=1, zone=BrickDetailviewLocation.LEFT, model=FakeContact,
        )

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            zone=BrickDetailviewLocation.RIGHT, model=FakeContact,
        )
        create_bdl(brick=rbi.brick_id, order=2)
        create_bdl(brick=rbrick_id,    order=3)

        create_contact = partial(FakeContact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')
        uran  = create_contact(first_name='Uran', last_name='Ochanomizu')

        create_rel = partial(Relation.objects.create, subject_entity=atom, user=user)
        create_rel(type=rtype1, object_entity=tenma)
        create_rel(type=rtype2, object_entity=uran)

        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/relations.html')
        self.assertTemplateUsed(response, 'creme_core/bricks/specific-relations.html')

        document = self.get_html_tree(response.content)
        rel_brick_node = self.get_brick_node(document, rbrick_id)

        reloading_info = {'include': [rtype1.id]}
        self.assertEqual(
            json_dump(reloading_info, separators=(',', ':')),
            rel_brick_node.attrib.get('data-brick-reloading-info')
        )
        self.assertInstanceLink(rel_brick_node, tenma)
        self.assertInstanceLink(rel_brick_node, uran)

        rbi_brick_node = self.get_brick_node(document, rbi.brick_id)
        self.assertIsNone(rbi_brick_node.attrib.get('data-brick-reloading-info'))
        self.assertInstanceLink(rbi_brick_node, tenma)
        self.assertNoInstanceLink(rbi_brick_node, uran)

        # Reloading
        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={
                'brick_id': rbrick_id,
                'extra_data': json_dump({rbrick_id: reloading_info}),
            },
        )

        load_data = response.json()
        self.assertEqual(load_data[0][0], rbrick_id)

        l_document = self.get_html_tree(load_data[0][1])
        l_rel_brick_node = self.get_brick_node(l_document, rbrick_id)
        self.assertInstanceLink(l_rel_brick_node, tenma)
        self.assertInstanceLink(l_rel_brick_node, uran)

    def test_relations_brick03(self):
        """With A SpecificRelationBrick ; the concerned relationship is minimal_display=True,
        so the RelationType is excluded.
        """
        user = self.login()
        rbrick_id = RelationsBrick.id_

        rtype1 = RelationType.create(
            ('test-subject_son',   'is the son of'),
            ('test-object_father', 'is the father of'),
            minimal_display=(True, True),
        )[0]
        rtype2 = RelationType.create(
            ('test-subject_brother', 'is the brother of'),
            ('test-object_sister',   'is the sister of')
        )[0]
        rbi = RelationBrickItem.objects.create_if_needed(rtype1)

        BrickDetailviewLocation.objects.create_for_model_brick(
            order=1, zone=BrickDetailviewLocation.LEFT, model=FakeContact,
        )

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            zone=BrickDetailviewLocation.RIGHT, model=FakeContact,
        )
        create_bdl(brick=rbi.brick_id, order=2)
        create_bdl(brick=rbrick_id,    order=3)

        create_contact = partial(FakeContact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')
        uran  = create_contact(first_name='Uran', last_name='Ochanomizu')

        create_rel = partial(Relation.objects.create, subject_entity=atom, user=user)
        create_rel(type=rtype1, object_entity=tenma)
        create_rel(type=rtype2, object_entity=uran)

        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/relations.html')
        self.assertTemplateUsed(response, 'creme_core/bricks/specific-relations.html')

        document = self.get_html_tree(response.content)

        rel_brick_node = self.get_brick_node(document, rbrick_id)
        self.assertInstanceLink(rel_brick_node, uran)
        self.assertNoInstanceLink(rel_brick_node, tenma)

        reloading_info = {'exclude': [rtype1.id]}
        self.assertEqual(
            json_dump(reloading_info, separators=(',', ':')),
            rel_brick_node.attrib.get('data-brick-reloading-info')
        )

        # Reloading
        response = self.assertGET200(
            reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
            data={
                'brick_id': rbrick_id,
                'extra_data': json_dump({rbrick_id: reloading_info}),
            },
        )

        load_data = response.json()
        self.assertEqual(load_data[0][0], rbrick_id)

        l_document = self.get_html_tree(load_data[0][1])
        l_rel_brick_node = self.get_brick_node(l_document, rbrick_id)
        self.assertNoInstanceLink(l_rel_brick_node, tenma)
        self.assertInstanceLink(l_rel_brick_node, uran)

        # Reloading + bad data
        def assertBadData(data):
            self.assertGET200(
                reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
                data={
                    'brick_id': rbrick_id,
                    'extra_data': json_dump({rbrick_id: data}),
                },
            )

        assertBadData(1)
        assertBadData({'include': 1})
        assertBadData({'exclude': 1})
        assertBadData({'include': [[]]})
        assertBadData({'exclude': [[]]})

    def _get_contact_brick_content(self, contact, brick_id):
        response = self.assertGET200(contact.get_absolute_url())
        document = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(document, brick_id)

        content_node = brick_node.find('.//div[@class="brick-content "]')
        self.assertIsNotNone(content_node)

        return content_node

    def _assertNoBrickTile(self, content_node, key):
        self.assertIsNone(content_node.find(f'.//div[@data-key="{key}"]'))

    def test_display_objectbrick01(self):
        user = self.login()
        naru = FakeContact.objects.create(
            user=user, last_name='Narusegawa', first_name='Naru', phone='1122334455',
        )

        content_node = self._get_contact_brick_content(naru, brick_id=MODELBRICK_ID)
        self.assertEqual(
            naru.last_name,
            self.get_brick_tile(content_node, 'regular_field-last_name').text,
        )
        self.assertIn(
            naru.phone,
            self.get_brick_tile(content_node, 'regular_field-phone').text
        )

    def test_display_objectbrick02(self):
        "With FieldsConfig"
        user = self.login()

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
        )
        naru = FakeContact.objects.create(
            user=user, last_name='Narusegawa',
            first_name='Naru', phone='1122334455',
        )

        content_node = self._get_contact_brick_content(naru, brick_id=MODELBRICK_ID)
        self.assertEqual(
            naru.last_name,
            self.get_brick_tile(content_node, 'regular_field-last_name').text
        )
        self._assertNoBrickTile(content_node, 'regular_field-phone')

    def test_display_custombrick01(self):
        user = self.login()

        fname1 = 'last_name'
        fname2 = 'phone'
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBrickConfigItem.objects.create(
            id='tests-contacts1', name='Contact info',
            content_type=FakeContact,
            cells=[
                build_cell(FakeContact, fname1),
                build_cell(FakeContact, fname2),
            ],
        )
        bdl = BrickDetailviewLocation.objects.create_if_needed(
            brick=cbc_item.brick_id,
            order=1000,
            model=FakeContact,
            zone=BrickDetailviewLocation.BOTTOM,
        )
        naru = FakeContact.objects.create(
            user=user, last_name='Narusegawa', first_name='Naru', phone='1122334455',
        )

        content_node = self._get_contact_brick_content(naru, brick_id=bdl.brick_id)
        self.assertEqual(
            naru.last_name,
            self.get_brick_tile(content_node, 'regular_field-last_name').text
        )
        self.assertIn(
            naru.phone,
            self.get_brick_tile(content_node, 'regular_field-phone').text
        )

    def test_display_custombrick02(self):
        "With FieldsConfig."
        user = self.login()

        hidden_fname = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBrickConfigItem.objects.create(
            id='tests-contacts1', name='Contact info',
            content_type=FakeContact,
            cells=[
                build_cell(FakeContact, 'last_name'),
                build_cell(FakeContact, hidden_fname),
            ],
        )
        bdl = BrickDetailviewLocation.objects.create_if_needed(
            brick=cbc_item.brick_id,
            order=1000,
            model=FakeContact,
            zone=BrickDetailviewLocation.BOTTOM,
        )
        naru = FakeContact.objects.create(
            user=user, last_name='Narusegawa', first_name='Naru', phone='1122334455',
        )

        content_node = self._get_contact_brick_content(naru, brick_id=bdl.brick_id)
        self.assertEqual(
            naru.last_name,
            self.get_brick_tile(content_node, 'regular_field-last_name').text,
        )
        self._assertNoBrickTile(content_node, 'regular_field-phone')

    def test_display_custombrick03(self):
        "With FieldsConfig on sub-fields."
        user = self.login()

        hidden_fname = 'zipcode'
        FieldsConfig.objects.create(
            content_type=FakeAddress,
            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
        )
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBrickConfigItem.objects.create(
            id='tests-contacts1', name='Contact info',
            content_type=FakeContact,
            cells=[
                build_cell(FakeContact, 'last_name'),
                build_cell(FakeContact, 'address__' + hidden_fname),
                build_cell(FakeContact, 'address__city'),
            ],
        )
        bdl = BrickDetailviewLocation.objects.create_if_needed(
            brick=cbc_item.brick_id,
            order=1000,  # Should be the last block
            model=FakeContact,
            zone=BrickDetailviewLocation.BOTTOM,
        )
        naru = FakeContact.objects.create(
            user=user, last_name='Narusegawa', first_name='Naru', phone='1122334455',
        )
        naru.address = FakeAddress.objects.create(
            value='Hinata Inn', city='Tokyo', zipcode='112233', entity=naru,
        )
        naru.save()

        content_node = self._get_contact_brick_content(naru, brick_id=bdl.brick_id)
        self.assertEqual(
            naru.last_name,
            self.get_brick_tile(content_node, 'regular_field-last_name').text,
        )
        self.assertEqual(
            naru.address.city,
            self.get_brick_tile(content_node, 'regular_field-address__city').text,
        )
        self._assertNoBrickTile(content_node, 'regular_field-address__zipcode')
