# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.translation import gettext as _

    from creme.creme_core.creme_jobs import deletor_type
    from creme.creme_core.models import (
        CremeEntity,
        CustomField, CustomFieldEnum, CustomFieldMultiEnum, CustomFieldEnumValue,
        Job, DeletionCommand,
        FakeContact, FakeOrganisation,
    )
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.views.base import BrickTestCaseMixin

    from creme.creme_config import bricks
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class CustomFieldsTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_portal(self):
        self.login()
        response = self.assertGET200(reverse('creme_config__custom_fields'))
        # self.assertTemplateUsed(response, 'creme_config/custom_fields_portal.html')
        self.assertTemplateUsed(response, 'creme_config/custom_field/portal.html')
        self.assertEqual(reverse('creme_core__reload_bricks'),
                         response.context.get('bricks_reload_url')
                        )

    def test_add_ct01(self):
        self.login(is_superuser=False, admin_4_apps=('creme_core',))
        self.assertFalse(CustomField.objects.all())

        url = reverse('creme_config__create_first_ctype_custom_field')
        context = self.assertGET200(url).context
        self.assertEqual(_('New custom field configuration'), context.get('title'))
        self.assertEqual(_('Save the custom field'),          context.get('submit_label'))

        ct = ContentType.objects.get_for_model(FakeContact)
        name = 'Size'
        field_type = CustomField.INT
        self.assertNoFormError(self.client.post(
            url,
            data={
                'content_type': ct.id,
                'name':         name,
                'field_type':   field_type,
            },
        ))

        cfields = CustomField.objects.all()
        self.assertEqual(1, len(cfields))

        cfield = cfields[0]
        self.assertEqual(ct,         cfield.content_type)
        self.assertEqual(name,       cfield.name)
        self.assertEqual(field_type, cfield.field_type)
        self.assertIs(cfield.is_required, False)

        response = self.assertGET200(url)

        with self.assertNoException():
            ctypes = response.context['form'].fields['content_type'].ctypes

        self.assertNotIn(ct, ctypes)
        self.assertIn(ContentType.objects.get_for_model(FakeOrganisation), ctypes)

    def test_add_ct02(self):
        self.login()

        ct = ContentType.objects.get_for_model(FakeContact)
        name = 'Eva'
        field_type = CustomField.ENUM
        self.assertNoFormError(self.client.post(
            reverse('creme_config__create_first_ctype_custom_field'),
            data={
                'content_type': ct.id,
                'name':         name,
                'is_required':  'on',
                'field_type':   field_type,
                'enum_values': 'Eva01\nEva02\nEva03',
            },
        ))

        cfield = self.get_object_or_fail(CustomField, content_type=ct.id, name=name)
        self.assertEqual(field_type, cfield.field_type)
        self.assertIs(cfield.is_required, True)

    def test_add_ct_error01(self):
        "Empty choice list."
        self.login()
        ct = ContentType.objects.get_for_model(FakeContact)
        self.assertFalse(CustomField.objects.filter(content_type=ct))

        response = self.assertPOST200(
            reverse('creme_config__create_first_ctype_custom_field'),
            data={
                'content_type': ct.id,
                'name':         'Eva',
                'field_type':   CustomField.ENUM,
                # 'enum_values': ...  #  NOPE
        })
        self.assertFormError(
            response, 'form', None,
            _('The choices list must not be empty if you choose the type "Choice list".')
        )

    def test_add_ct_error02(self):
        "Duplicated choices."
        self.login()
        response = self.assertPOST200(
            reverse('creme_config__create_first_ctype_custom_field'),
            data={
                'content_type': ContentType.objects.get_for_model(FakeContact).id,
                'name':        'Eva',
                'field_type':  CustomField.ENUM,
                'enum_values': 'Eva01\nEva02\nEva01',
            },
        )
        self.assertFormError(
            response, 'form', 'enum_values',
            _('The choice «{}» is duplicated.').format('Eva01')
        )

    def test_add_ct_error03(self):
        self.login(is_superuser=False)  # admin_4_apps=('creme_core',)
        self.assertGET403(reverse('creme_config__create_first_ctype_custom_field'))

    def test_delete_ct01(self):
        self.login(is_superuser=False, admin_4_apps=('creme_core',))

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(FakeContact)
        ct_orga    = get_ct(FakeOrganisation)

        create_cf = CustomField.objects.create
        cfield1 = create_cf(content_type=ct_contact, name='CF#1', field_type=CustomField.INT)
        cfield2 = create_cf(content_type=ct_contact, name='CF#2', field_type=CustomField.FLOAT)
        cfield3 = create_cf(content_type=ct_orga,    name='CF#3', field_type=CustomField.BOOL)
        self.assertPOST200(reverse('creme_config__delete_ctype_custom_fields'), data={'id': ct_contact.id})
        self.assertFalse(CustomField.objects.filter(pk__in=[cfield1.pk, cfield2.pk]))
        self.assertStillExists(cfield3)

    def test_delete_ct02(self):
        self.login(is_superuser=False)

        ct_contact = ContentType.objects.get_for_model(FakeContact)
        CustomField.objects.create(
            content_type=ct_contact,
            name='Size',
            field_type=CustomField.INT,
        )
        self.assertPOST403(
            reverse('creme_config__delete_ctype_custom_fields'),
            data={'id': ct_contact.id},
        )

    def test_add01(self):
        self.login(is_superuser=False, admin_4_apps=('creme_core',))

        get_ct = ContentType.objects.get_for_model
        contact_ct = get_ct(FakeContact)
        orga_ct    = get_ct(FakeOrganisation)

        name = 'Eva'
        create_cf = CustomField.objects.create
        create_cf(content_type=contact_ct, field_type=CustomField.BOOL, name='Operational?')
        create_cf(content_type=orga_ct,    field_type=CustomField.INT,  name=name)  # <= same name but not same CT

        url = reverse('creme_config__create_custom_field', args=(contact_ct.id,))
        context = self.assertGET200(url).context
        self.assertEqual(_('New custom field for «{model}»').format(model='Test Contact'),
                         context.get('title')
                        )
        self.assertEqual(_('Save the custom field'), context.get('submit_label'))

        field_type = CustomField.ENUM
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name':        name,
                'field_type':  field_type,
                'enum_values': 'Eva01\nEva02\nEva03',
            },
        ))

        cfields = CustomField.objects.filter(content_type=contact_ct).order_by('id')
        self.assertEqual(2, len(cfields))

        cfield2 = cfields[1]
        self.assertEqual(name, cfield2.name)
        self.assertFalse(cfield2.is_required)
        self.assertEqual(field_type, cfield2.field_type)
        self.assertEqual(
            ['Eva01', 'Eva02', 'Eva03'],
            [cfev.value
                for cfev in CustomFieldEnumValue.objects
                                                .filter(custom_field=cfield2)
                                                .order_by('id')
            ]
        )

    def test_add02(self):
        "content_type + name => unique together."
        self.login()

        ct = ContentType.objects.get_for_model(FakeContact)
        name = 'Rating'
        CustomField.objects.create(content_type=ct, name=name, field_type=CustomField.FLOAT)

        field_type = CustomField.INT
        response = self.assertPOST200(
            reverse('creme_config__create_custom_field', args=(ct.id,)),
            data={
                'name':       name,
                'field_type': field_type,
            },
        )
        self.assertFormError(
            response, 'form', 'name',
            _('There is already a custom field with this name.')
        )

    def test_add03(self):
        "Empty list of choices."
        self.login()

        contact_ct = ContentType.objects.get_for_model(FakeContact)
        response = self.assertPOST200(
            reverse('creme_config__create_custom_field', args=(contact_ct.id,)),
            data={
                'name':        'Eva',
                'field_type':  CustomField.ENUM,
                'enum_values': '',
            }
        )
        self.assertFormError(
            response, 'form', None,
            _('The choices list must not be empty if you choose the type "Choice list".')
        )

    def test_add04(self):
        "Duplicated choices."
        self.login()

        contact_ct = ContentType.objects.get_for_model(FakeContact)
        response = self.assertPOST200(
            reverse('creme_config__create_custom_field', args=(contact_ct.id,)),
            data={
                'name':        'Eva',
                'field_type':  CustomField.ENUM,
                'enum_values': 'Eva01\nEva02\nEva01',
            }
        )
        self.assertFormError(
            response, 'form', 'enum_values',
            _('The choice «{}» is duplicated.').format('Eva01')
        )

    def test_edit01(self):
        self.login(is_superuser=False, admin_4_apps=('creme_core',))

        name = 'nickname'
        cfield = CustomField.objects.create(
            content_type=FakeContact,
            name=name,
            field_type=CustomField.STR,
        )
        self.assertFalse(cfield.is_required)

        url = reverse('creme_config__edit_custom_field', args=(cfield.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit «{object}»').format(object=cfield), context.get('title'))

        # ---
        name = name.title()
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name': name,
                'is_required': 'on',
            }
        ))

        cfield = self.refresh(cfield)
        self.assertEqual(name, cfield.name)
        self.assertTrue(cfield.is_required)

    # def test_edit02(self):
    #     "ENUM."
    #     self.login()
    #
    #     ct = ContentType.objects.get_for_model(FakeContact)
    #     create_cfield = partial(CustomField.objects.create,
    #                             content_type=ct,
    #                             field_type=CustomField.MULTI_ENUM,
    #                            )
    #     cfield1 = create_cfield(name='Programming languages')
    #     cfield2 = create_cfield(name='Countries')
    #
    #     create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield1)
    #     create_evalue(value='C')
    #     create_evalue(value='ABC')
    #     create_evalue(value='Java')
    #     create_evalue(value='Haskell', custom_field=cfield2)  # Should be ignored as dupliacte
    #
    #     url = reverse('creme_config__edit_custom_field', args=(cfield1.id,))
    #     response = self.assertGET200(url)
    #
    #     with self.assertNoException():
    #         fields = response.context['form'].fields
    #         new_choices = fields['new_choices']
    #         old_choices = fields['old_choices']
    #
    #     self.assertFalse(new_choices.initial)
    #     self.assertEqual(['C', 'ABC', 'Java'], old_choices.content)
    #
    #     response = self.client.post(
    #         url,
    #         data={
    #             'name': cfield1.name,
    #             'new_choices': 'C++\nHaskell',
    #
    #             'old_choices_check_0': 'on',
    #             'old_choices_value_0': 'C',
    #
    #             'old_choices_check_1': 'on',
    #             'old_choices_value_1': 'Python',
    #         },
    #     )
    #     self.assertNoFormError(response)
    #
    #     self.assertEqual(
    #         ['C', 'Python', 'C++', 'Haskell'],
    #         [cfev.value
    #             for cfev in CustomFieldEnumValue.objects
    #                                             .filter(custom_field=cfield1)
    #                                             .order_by('id')
    #         ]
    #     )
    #
    # def test_edit03(self):
    def test_edit02(self):
        "content_type + name => unique together."
        self.login()

        name = 'Nickname'
        create_cfield = partial(CustomField.objects.create,
                                content_type=FakeContact,
                                field_type=CustomField.STR
                               )
        create_cfield(name=name)
        cfield2 = create_cfield(name='Label')

        response = self.assertPOST200(
            reverse('creme_config__edit_custom_field', args=(cfield2.id,)),
            data={'name': name},
        )
        self.assertFormError(
            response, 'form', 'name',
            _('There is already a custom field with this name.')
        )

    def test_delete01(self):
        self.login(is_superuser=False, admin_4_apps=('creme_core',))

        create_cf = partial(CustomField.objects.create, content_type=FakeContact)
        cfield1 = create_cf(name='Day',       field_type=CustomField.DATETIME)
        cfield2 = create_cf(name='Languages', field_type=CustomField.ENUM)
        cfield3 = create_cf(name='Hobbies',   field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        eval1 = create_evalue(custom_field=cfield2, value='C')
        eval2 = create_evalue(custom_field=cfield2, value='Python')
        eval3 = create_evalue(custom_field=cfield3, value='Programming')
        eval4 = create_evalue(custom_field=cfield3, value='Reading')

        self.assertPOST200(reverse('creme_config__delete_custom_field'), data={'id': cfield2.id})

        self.assertStillExists(cfield1)
        self.assertStillExists(cfield3)
        self.assertDoesNotExist(cfield2)

        self.assertStillExists(eval3)
        self.assertStillExists(eval4)
        self.assertDoesNotExist(eval1)
        self.assertDoesNotExist(eval2)

    def test_delete02(self):
        self.login(is_superuser=False)  # admin_4_apps=('creme_core',)

        cfield = CustomField.objects.create(
            name='Day',
            content_type=FakeContact,
            field_type=CustomField.DATETIME,
        )

        self.assertPOST403(
            reverse('creme_config__delete_custom_field'),
            data={'id': cfield.id},
        )

    def test_enum_values_detail(self):
        self.login(is_superuser=False, admin_4_apps=('creme_core',))

        ct = ContentType.objects.get_for_model(FakeContact)
        create_cfield = partial(CustomField.objects.create, content_type=ct)
        cfield1 = create_cfield(name='Countries',
                                field_type=CustomField.ENUM,
                               )

        response = self.assertGET200(
            reverse('creme_config__custom_enums', args=(cfield1.id,))
        )
        self.assertTemplateUsed(
            response,
            'creme_config/custom_field/enums.html'
        )
        context = response.context
        self.assertEqual(cfield1, context.get('custom_field'))
        self.assertEqual(
            reverse('creme_config__reload_custom_enum_brick', args=(cfield1.id,)),
            context.get('bricks_reload_url')
        )

        self.get_brick_node(
            self.get_html_tree(response.content),
            bricks.CustomEnumsBrick.id_
        )

        cfield2 = create_cfield(name='Programming languages',
                                field_type=CustomField.MULTI_ENUM,
                               )
        self.assertGET200(
            reverse('creme_config__custom_enums', args=(cfield2.id,))
        )

        cfield3 = create_cfield(name='Details', field_type=CustomField.STR)
        self.assertGET409(
            reverse('creme_config__custom_enums', args=(cfield3.id,))
        )

    def test_add_enum_values01(self):
        self.login(is_superuser=False, admin_4_apps=('creme_core',))

        ct = ContentType.objects.get_for_model(FakeContact)
        create_cfield = partial(CustomField.objects.create,
                                content_type=ct,
                                field_type=CustomField.ENUM,
                               )
        cfield1 = create_cfield(name='Programming languages')
        cfield2 = create_cfield(name='Countries')

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield1)
        create_evalue(value='C')
        create_evalue(value='ABC')
        create_evalue(value='Java')
        create_evalue(value='Haskell', custom_field=cfield2)  # Should be ignored as duplicate

        url = reverse('creme_config__add_custom_enums', args=(cfield1.id,))
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'choices': 'C++\nHaskell',
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(
            ['C', 'ABC', 'Java', 'C++', 'Haskell'],
            [cfev.value
                for cfev in CustomFieldEnumValue.objects
                                                .filter(custom_field=cfield1)
                                                .order_by('id')
            ]
        )

    def test_add_enum_values02(self):
        "MULTI_ENUM + duplicated choice."
        self.login()

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            name='Programming languages',
            field_type=CustomField.MULTI_ENUM,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        eval01 = create_evalue(value='C')
        __     = create_evalue(value='Java')

        url = reverse('creme_config__add_custom_enums', args=(cfield.id,))
        data = {
            'choices': f'C++\n{eval01.value}',
        }

        response1 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response1, 'form', 'choices',
            _('The choice «{}» is duplicated.').format(eval01.value)
        )

        response2 = self.assertPOST200(
            url,
            data={
                **data,
                'choices': 'Ocaml\nErlang\nOcaml',
            },
        )
        self.assertFormError(
            response2, 'form', 'choices',
            _('The choice «{}» is duplicated.').format('Ocaml')
        )

    def test_add_enum_values03(self):
        "Not Enum type => error."
        self.login()

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            name='Programming languages',
            field_type=CustomField.STR,
        )
        self.assertGET409(
            reverse('creme_config__add_custom_enums', args=(cfield.id,))
        )

    def test_add_enum_values04(self):
        "Not allowed."
        self.login(is_superuser=False)

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            name='Programming languages',
            field_type=CustomField.MULTI_ENUM,
        )

        self.assertGET403(
            reverse('creme_config__add_custom_enums', args=(cfield.id,))
        )

    def test_add_enum_value01(self):
        self.login(is_superuser=False, admin_4_apps=('creme_core',))

        ct = ContentType.objects.get_for_model(FakeContact)
        create_cfield = partial(CustomField.objects.create,
                                content_type=ct,
                                field_type=CustomField.ENUM,
                               )
        cfield1 = create_cfield(name='Programming languages')
        cfield2 = create_cfield(name='Countries')

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield1)
        create_evalue(value='C')
        create_evalue(value='ABC')
        create_evalue(value='Java')
        create_evalue(value='Haskell', custom_field=cfield2)  # Should be ignored as duplicate

        url = reverse('creme_config__add_custom_enum', args=(cfield1.id,))
        response = self.assertGET200(url)
        self.assertEqual(
            _('Add this new choice'),
            response.context.get('submit_label')
        )

        response = self.client.post(
            url,
            data={
                'choice': 'Haskell',
            },
        )
        self.assertNoFormError(response)

        evalues = CustomFieldEnumValue.objects.filter(custom_field=cfield1).order_by('id')
        self.assertEqual(
            ['C', 'ABC', 'Java', 'Haskell'],
            [cfev.value for cfev in evalues]
        )
        # self.assertWidgetResponse(response, evalues[3]) TODO ?
        created_evalue = evalues[3]
        self.assertDictEqual(
            {'added': [[created_evalue.id, str(created_evalue)]],
             'value': created_evalue.id,
            },
            response.json()
        )

    def test_add_enum_value02(self):
        "MULTI_ENUM + duplicated choice."
        self.login()

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            name='Programming languages',
            field_type=CustomField.MULTI_ENUM,
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        eval01 = create_evalue(value='C')
        __     = create_evalue(value='Java')

        response = self.assertPOST200(
            reverse('creme_config__add_custom_enum', args=(cfield.id,)),
            data={
                'choice': eval01.value,
            },
        )
        self.assertFormError(
            response, 'form', 'choice',
            _('The choice «{}» is duplicated.').format(eval01.value)
        )

    def test_add_enum_value03(self):
        "Not Enum type => error."
        self.login()

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            name='Programming languages',
            field_type=CustomField.STR,
        )
        self.assertGET409(
            reverse('creme_config__add_custom_enum', args=(cfield.id,))
        )

    def test_add_enum_value04(self):
        "Not allowed."
        self.login(is_superuser=False)

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            name='Programming languages',
            field_type=CustomField.MULTI_ENUM,
        )

        self.assertGET403(
            reverse('creme_config__add_custom_enum', args=(cfield.id,))
        )

    def test_edit_enum_value01(self):
        self.login(is_superuser=False, admin_4_apps=('creme_core',))

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
            name='Programming languages',
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        eval01 = create_evalue(value='C')
        eval02 = create_evalue(value='ABC')
        eval03 = create_evalue(value='Java')

        url = reverse('creme_config__edit_custom_enum', args=(eval02.id,))
        self.assertGET200(url)

        value = 'Python'
        response = self.client.post(
            url,
            data={
                'value': value,
            },
        )
        self.assertNoFormError(response)

        self.assertListEqual(
            [eval01.value, value, eval03.value],
            [cfev.value
                for cfev in CustomFieldEnumValue.objects
                                                .filter(custom_field=cfield)
                                                .order_by('id')
            ]
        )

    def test_edit_enum_value02(self):
        "Not allowed."
        self.login(is_superuser=False)  # admin_4_apps=('creme_core',)

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
            name='Programming languages',
        )
        evalue = CustomFieldEnumValue.objects.create(custom_field=cfield, value='A')
        self.assertGET403(
            reverse('creme_config__edit_custom_enum', args=(evalue.id,))
        )

    def test_delete_enum_value01(self):
        "ENUM not used."
        user = self.login(is_superuser=False, admin_4_apps=('creme_core',))

        self.assertIsNone(DeletionCommand.objects.first())

        cfield = CustomField.objects.create(content_type=FakeContact,
                                            name='Programming languages',
                                            field_type=CustomField.ENUM,
                                           )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        __     = create_evalue(value='C')
        eval02 = create_evalue(value='bash')
        __     = create_evalue(value='sh')

        url = reverse('creme_config__delete_custom_enum', args=(eval02.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(
            response,
            'creme_core/generics/blockform/delete-popup.html'
        )

        context = response.context
        self.assertEqual(
            _('Replace & delete «{object}»').format(object=eval02.value),
            context.get('title')
        )
        self.assertEqual(_('Delete the choice'), context.get('submit_label'))

        with self.assertNoException():
            fields = context['form'].fields
            info = fields['info']

        self.assertFalse(info.required)
        self.assertNotIn('to_choice', fields)

        response = self.client.post(url)
        self.assertNoFormError(response)
        self.assertTemplateUsed(response, 'creme_config/deletion-job-popup.html')

        dcom = self.get_deletion_command_or_fail(CustomFieldEnumValue)
        self.assertEqual(eval02,       dcom.instance_to_delete)
        self.assertEqual(eval02.value, dcom.deleted_repr)
        self.assertFalse(
            dcom.replacers
        )
        self.assertEqual(0, dcom.total_count)
        self.assertEqual(0, dcom.updated_count)

        job = dcom.job
        self.assertEqual(deletor_type.id, job.type_id)
        self.assertEqual(user, job.user)

        deletor_type.execute(job)
        self.assertDoesNotExist(eval02)

    def test_delete_enum_value02(self):
        "ENUM used + replacing."
        user = self.login()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=FakeContact,
            field_type=CustomField.ENUM,
        )
        cfield1 = create_cfield(name='Programming languages')
        cfield2 = create_cfield(name='OS')

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield1)
        eval1_01 = create_evalue(value='C')
        eval1_02 = create_evalue(value='C99')
        eval1_03 = create_evalue(value='lisp')
        eval2_01 = create_evalue(value='Linux', custom_field=cfield2)

        create_contact = partial(FakeContact.objects.create, user=user)
        linus   = create_contact(first_name='Linus',   last_name='Torvalds')
        richard = create_contact(first_name='Richard', last_name='Stallman')

        create_enum = partial(CustomFieldEnum.objects.create, custom_field=cfield1)
        enum1 = create_enum(entity=linus, value=eval1_02)
        enum2 = create_enum(entity=richard, value=eval1_03)

        url = reverse('creme_config__delete_custom_enum', args=(eval1_02.id,))
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            choices = [*fields['to_choice'].choices]

        self.assertNotIn('info', fields)

        self.assertInChoices(value='',          label='---------',    choices=choices)
        self.assertInChoices(value=eval1_01.id, label=eval1_01.value, choices=choices)
        self.assertInChoices(value=eval1_03.id, label=eval1_03.value, choices=choices)
        self.assertNotInChoices(value=eval1_02.id, choices=choices)
        self.assertNotInChoices(value=eval2_01.id, choices=choices)

        response = self.client.post(url, data={'to_choice': eval1_01.id})
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(CustomFieldEnumValue)
        self.assertEqual(eval1_02, dcom.instance_to_delete)
        self.assertListEqual(
            [('fixed_value', CustomFieldEnum, 'value', eval1_01)],
            [(r.type_id, r.model_field.model, r.model_field.name, r.get_value())
                for r in dcom.replacers
            ]
        )
        self.assertEqual(1, dcom.total_count)
        self.assertEqual(0, dcom.updated_count)

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(eval1_02)

        self.assertEqual(eval1_03, self.refresh(enum2).value)
        self.assertEqual(eval1_01, self.refresh(enum1).value)

    def test_delete_enum_value03(self):
        "ENUM used + replacing by NULL."
        user = self.login()

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.ENUM,
            name='Programming languages',
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        eval1_01 = create_evalue(value='C')
        __       = create_evalue(value='lisp')

        linus = FakeContact.objects.create(user=user, first_name='Linus', last_name='Torvalds')

        enum1 = CustomFieldEnum.objects.create(
            entity=linus, custom_field=cfield, value=eval1_01,
        )

        response = self.client.post(
            reverse('creme_config__delete_custom_enum', args=(eval1_01.id,)),
            # data={'to_choice': eval1_02.id}
        )
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(CustomFieldEnumValue)
        self.assertFalse(dcom.replacers)
        self.assertEqual(1, dcom.total_count)

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(eval1_01)
        self.assertDoesNotExist(enum1)

    def test_delete_enum_value04(self):
        "Not allowed."
        self.login(is_superuser=False)  # admin_4_apps=('creme_core',)

        cfield = CustomField.objects.create(content_type=FakeContact,
                                            name='Programming languages',
                                            field_type=CustomField.ENUM,
                                           )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        __     = create_evalue(value='C')
        eval02 = create_evalue(value='bash')

        self.assertGET403(
            reverse('creme_config__delete_custom_enum', args=(eval02.id,))
        )

    def test_delete_enum_value05(self):
        "Uniqueness."
        user = self.login()

        self.assertFalse(DeletionCommand.objects.first())

        cfield = CustomField.objects.create(content_type=FakeContact,
                                            name='Programming languages',
                                            field_type=CustomField.ENUM,
                                           )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        eval01 = create_evalue(value='C')
        eval02 = create_evalue(value='C89')
        __     = create_evalue(value='Java')

        job1 = Job.objects.create(type_id=deletor_type.id, user=user)
        job2 = Job.objects.create(type_id=deletor_type.id, user=user)
        self.assertEqual(Job.STATUS_WAIT, job1.status)

        get_ct = ContentType.objects.get_for_model
        self.assertLess(get_ct(CremeEntity).id, get_ct(CustomFieldEnumValue).id)

        dcom1 = DeletionCommand.objects.create(
            job=job2,
            instance_to_delete=CremeEntity.objects.create(user=user),
        )
        dcom2 = DeletionCommand.objects.create(
            job=job1,
            instance_to_delete=eval01,
        )

        url = reverse('creme_config__delete_custom_enum', args=(eval02.id,))
        response = self.assertGET409(url)
        msg = _('A deletion process for a choice already exists.')
        self.assertIn(msg, response.content.decode())

        # ---
        job1.status = Job.STATUS_ERROR
        job1.save()
        response = self.assertGET409(url)
        self.assertIn(msg, response.content.decode())

        # ---
        job1.status = Job.STATUS_OK
        job1.save()
        response = self.assertGET200(url)
        self.assertIn('form', response.context)
        self.assertDoesNotExist(job1)
        self.assertDoesNotExist(dcom2)
        self.assertStillExists(dcom1)

    def test_delete_multi_enum01(self):
        "MULTI_ENUM not used."
        user = self.login(is_superuser=False, admin_4_apps=('creme_core',))

        cfield = CustomField.objects.create(content_type=FakeContact,
                                            name='Programming languages',
                                            field_type=CustomField.MULTI_ENUM,
                                           )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        __     = create_evalue(value='C')
        eval02 = create_evalue(value='bash')
        __     = create_evalue(value='sh')

        url = reverse('creme_config__delete_custom_enum', args=(eval02.id,))
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            info = fields['info']

        self.assertFalse(info.required)
        self.assertNotIn('to_choice', fields)

        response = self.client.post(url)
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(CustomFieldEnumValue)
        self.assertEqual(eval02,       dcom.instance_to_delete)
        self.assertEqual(eval02.value, dcom.deleted_repr)
        self.assertFalse(
            dcom.replacers
        )
        self.assertEqual(0, dcom.total_count)

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(eval02)

    def test_delete_multi_enum02(self):
        "MULTI_ENUM used + replacing."
        user = self.login()

        create_cfield = partial(
            CustomField.objects.create,
            content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
        )
        cfield1 = create_cfield(name='Programming languages')
        cfield2 = create_cfield(name='OS')

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield1)
        eval1_01 = create_evalue(value='C')
        eval1_02 = create_evalue(value='C99')
        eval1_03 = create_evalue(value='lisp')
        eval2_01 = create_evalue(value='Linux', custom_field=cfield2)

        create_contact = partial(FakeContact.objects.create, user=user)
        linus   = create_contact(first_name='Linus',   last_name='Torvalds')
        richard = create_contact(first_name='Richard', last_name='Stallman')
        john    = create_contact(first_name='John',    last_name='Carmack')

        cf_memum = partial(CustomFieldMultiEnum, custom_field=cfield1)
        cf_memum(entity=linus).set_value_n_save([eval1_02])
        cf_memum(entity=richard).set_value_n_save([eval1_01, eval1_03])
        cf_memum(entity=john).set_value_n_save([eval1_02, eval1_01])  # beware to avoid duplicates

        url = reverse('creme_config__delete_custom_enum', args=(eval1_02.id,))
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            choices = [*fields['to_choice'].choices]

        self.assertNotIn('info', fields)

        self.assertInChoices(value='',          label='---------',    choices=choices)
        self.assertInChoices(value=eval1_01.id, label=eval1_01.value, choices=choices)
        self.assertInChoices(value=eval1_03.id, label=eval1_03.value, choices=choices)
        self.assertNotInChoices(value=eval1_02.id, choices=choices)
        self.assertNotInChoices(value=eval2_01.id, choices=choices)

        response = self.client.post(url, data={'to_choice': eval1_01.id})
        self.assertNoFormError(response)

        dcom = self.get_deletion_command_or_fail(CustomFieldEnumValue)
        self.assertEqual(eval1_02, dcom.instance_to_delete)
        self.assertListEqual(
            [('fixed_value', CustomFieldMultiEnum, 'value', eval1_01)],
            [(r.type_id, r.model_field.model, r.model_field.name, r.get_value())
                for r in dcom.replacers
            ]
        )
        self.assertEqual(2, dcom.total_count)

        deletor_type.execute(dcom.job)
        self.assertDoesNotExist(eval1_02)

        self.assertCountEqual(
            [eval1_01, eval1_03],
            [*self.refresh(richard).get_custom_value(cfield1).get_enumvalues()]
        )
        self.assertCountEqual(
            [eval1_01],
            [*self.refresh(linus).get_custom_value(cfield1).get_enumvalues()]
        )
        self.assertCountEqual(
            [eval1_01],
            [*self.refresh(john).get_custom_value(cfield1).get_enumvalues()]
        )

    def test_reload_enum_brick01(self):
        self.login(is_superuser=False, admin_4_apps=('creme_core',))

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
            name='Programming languages',
        )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        eval01 = create_evalue(value='C')
        eval02 = create_evalue(value='ABC')
        eval03 = create_evalue(value='Java')

        response = self.assertGET200(
            reverse('creme_config__reload_custom_enum_brick',
                    args=(cfield.id,),
                   )
        )

        results = response.json()
        self.assertIsInstance(results, list)
        self.assertEqual(1, len(results))

        result = results[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))

        brick_id = bricks.CustomEnumsBrick.id_
        self.assertEqual(brick_id, result[0])
        brick_node = self.get_brick_node(self.get_html_tree(result[1]), brick_id)

        values = {node.text for node in brick_node.findall('.//td')}
        self.assertIn(eval01.value, values)
        self.assertIn(eval02.value, values)
        self.assertIn(eval03.value, values)

    def test_reload_enum_brick02(self):
        "Not allowed."
        self.login(is_superuser=False)  # admin_4_apps=('creme_core',)

        cfield = CustomField.objects.create(
            content_type=FakeContact,
            field_type=CustomField.MULTI_ENUM,
            name='Programming languages',
        )
        self.assertGET403(
            reverse('creme_config__reload_custom_enum_brick',
                    args=(cfield.id,),
                   )
        )
