# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import (Relation, RelationType, SetCredentials,
            ButtonMenuItem, FieldsConfig)

    from creme.persons import get_address_model, get_contact_model, get_organisation_model
    from creme.persons.models import Civility
    from creme.persons.constants import REL_OBJ_EMPLOYED_BY
    from creme.persons.tests.base import (skipIfCustomAddress, skipIfCustomContact,
            skipIfCustomOrganisation)

    from creme.vcfs.buttons import GenerateVcfButton
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


Address = get_address_model()
Contact = get_contact_model()
Organisation = get_organisation_model()


@skipIfCustomContact
class VcfExportTestCase(CremeTestCase):
    def _generate_vcf(self, contact, status_code=200):
        response = self.client.get(reverse('vcfs__export', args=(contact.id,)))
        self.assertEqual(status_code, response.status_code)

        return response

    def create_contact(self, **kwargs):
        fields = {
            'user': self.user,
            'last_name': 'Abitbol',
            'first_name': 'George',
            'phone': '0404040404',
            'mobile': '0606060606',
            'fax': '0505050505',
            'email': 'a@aa.fr',
            'url_site': 'www.aaa.fr',
        }
        fields.update(kwargs)

        return Contact.objects.create(**fields)

    def create_address(self, contact, prefix):
        return Address.objects.create(address='{}_address'.format(prefix),
                                      city='{}_city'.format(prefix),
                                      po_box='{}_po_box'.format(prefix),
                                      country='{}_country'.format(prefix),
                                      zipcode='{}_zipcode'.format(prefix),
                                      department='{}_department'.format(prefix),
                                      content_type_id=ContentType.objects.get_for_model(Contact).id,
                                      object_id=contact.id,
                                     )

    def test_button(self):
        self.login()
        ButtonMenuItem.create_if_needed(pk='vcfs-test_button', model=Contact,
                                        button=GenerateVcfButton, order=100,
                                       )

        contact = self.create_contact()
        response = self.assertGET200(contact.get_absolute_url())
        self.assertTemplateUsed(response, GenerateVcfButton.template_name)

    def test_get_empty_vcf(self):
        user = self.login()
        response = self._generate_vcf(Contact.objects.create(user=user, last_name='Abitbol'))
        self.assertEqual(b'BEGIN:VCARD\r\nVERSION:3.0\r\nFN: Abitbol\r\nN:Abitbol;;;;\r\nEND:VCARD\r\n',
                         response.content
                        )

    def test_get_vcf_basic_role(self):
        user = self.login(is_superuser=False,
                          allowed_apps=('creme_core', 'persons', 'vcfs'),
                          creatable_models=[Contact],
                         )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,  # Not EntityCredentials.VIEW
                                      set_type=SetCredentials.ESET_ALL
                                     )

        contact = Contact.objects.create(user=self.other_user, last_name='Abitbol')
        self.assertTrue(user.has_perm_to_change(contact))
        self.assertFalse(user.has_perm_to_view(contact))
        self._generate_vcf(contact, status_code=403)

    def test_get_vcf_civility(self):
        user = self.login()
        contact = Contact.objects.create(user=user,
                                         civility=Civility.objects.create(title='Monsieur'),
                                         last_name='Abitbol',
                                        )

        response = self._generate_vcf(contact)
        self.assertEqual(b'BEGIN:VCARD\r\nVERSION:3.0\r\nFN: Abitbol\r\nN:Abitbol;;;Monsieur;\r\nEND:VCARD\r\n',
                         response.content
                        )

    @skipIfCustomOrganisation
    def test_get_vcf_org(self):
        user = self.login()
        contact = Contact.objects.create(user=user, last_name='Abitbol')
        orga = Organisation.objects.create(user=user, name='ORGNAME')

        rtype = RelationType.objects.get(pk=REL_OBJ_EMPLOYED_BY)
        Relation.objects.create(type=rtype, subject_entity=orga, object_entity=contact, user=user)

        response = self._generate_vcf(contact)
        self.assertEqual(b'BEGIN:VCARD\r\nVERSION:3.0\r\nFN: Abitbol\r\nN:Abitbol;;;;\r\nORG:ORGNAME\r\nEND:VCARD\r\n',
                         response.content
                        )

    @skipIfCustomAddress
    def test_get_vcf_billing_addr(self):
        self.login()
        contact = self.create_contact(civility=Civility.objects.create(title='Mr'))
        contact.billing_address = self.create_address(contact, 'Org')
        contact.save()

        response = self._generate_vcf(contact)
        self.assertEqual(b'BEGIN:VCARD\r\nVERSION:3.0\r\nADR:Org_po_box;;Org_address;Org_city;Org_department;'
                         b'Org_zipcode;Org_countr\r\n y\r\nTEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
                         b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
                         b'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
                         response.content
                        )

    @skipIfCustomAddress
    def test_get_vcf_shipping_addr(self):
        self.login()
        contact = self.create_contact(civility=Civility.objects.create(title='Mr'))
        contact.shipping_address = self.create_address(contact, 'Org')
        contact.save()

        response = self._generate_vcf(contact)
        self.assertEqual(b'BEGIN:VCARD\r\nVERSION:3.0\r\nADR:Org_po_box;;Org_address;'
                         b'Org_city;Org_department;Org_zipcode;Org_countr\r\n y\r\n'
                         b'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
                         b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;'
                         b'\r\nTEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
                         response.content
                        )

    @skipIfCustomAddress
    def test_get_vcf_both_addr(self):
        self.login()
        contact = self.create_contact(civility=Civility.objects.create(title='Mr'))
        contact.shipping_address = self.create_address(contact, 'shipping')
        contact.billing_address = self.create_address(contact, 'billing')
        contact.save()

        response = self._generate_vcf(contact)
        self.assertEqual(b'BEGIN:VCARD\r\nVERSION:3.0\r\n'
                         b'ADR:shipping_po_box;;shipping_address;shipping_city;shipping_department;sh\r\n ipping_zipcode;shipping_country\r\n'
                         b'ADR:billing_po_box;;billing_address;billing_city;billing_department;billin\r\n g_zipcode;billing_country\r\n'
                         b'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
                         b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
                         b'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
                         response.content
                        )

    @skipIfCustomAddress
    def test_get_vcf_addr_eq(self):
        self.login()
        contact = self.create_contact(civility=Civility.objects.create(title='Mr'))
        contact.shipping_address = self.create_address(contact, 'Org')
        contact.billing_address = self.create_address(contact, 'Org')
        contact.save()
        self.create_address(contact, 'Org')  # Other_address

        response = self._generate_vcf(contact)
        self.assertEqual(b'BEGIN:VCARD\r\nVERSION:3.0\r\n'
                         b'ADR:Org_po_box;;Org_address;Org_city;Org_department;Org_zipcode;Org_countr\r\n y\r\n'
                         b'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
                         b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
                         b'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
                         response.content
                        )

    @skipIfCustomAddress
    def test_person(self):
        self.login()
        contact = self.create_contact(civility=Civility.objects.create(title='Mr'))
        contact.shipping_address = self.create_address(contact, 'shipping')
        contact.billing_address = self.create_address(contact, 'billing')
        contact.save()
        self.create_address(contact, 'Org')  # Other_address

        response = self._generate_vcf(contact)
        self.assertEqual(b'BEGIN:VCARD\r\nVERSION:3.0\r\n'
                         b'ADR:shipping_po_box;;shipping_address;shipping_city;shipping_department;sh\r\n ipping_zipcode;shipping_country\r\n'
                         b'ADR:billing_po_box;;billing_address;billing_city;billing_department;billin\r\n g_zipcode;billing_country\r\n'
                         b'ADR:Org_po_box;;Org_address;Org_city;Org_department;Org_zipcode;Org_countr\r\n y\r\n'
                         b'TEL;TYPE=CELL:0606060606\r\nEMAIL;TYPE=INTERNET:a@aa.fr\r\n'
                         b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;Mr;\r\n'
                         b'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
                         response.content
                        )

    @skipIfCustomAddress
    def test_fields_config(self):
        self.login()
        contact = self.create_contact()
        contact.billing_address = self.create_address(contact, 'billing')
        contact.save()

        create_fc = FieldsConfig.create
        create_fc(Contact,
                  descriptions=[('email', {FieldsConfig.HIDDEN: True})],
                 )
        create_fc(Address,
                  descriptions=[('zipcode', {FieldsConfig.HIDDEN: True})],
                 )

        response = self._generate_vcf(contact)
        self.assertEqual(b'BEGIN:VCARD\r\nVERSION:3.0\r\n'
                         b'ADR:billing_po_box;;billing_address;billing_city;billing_department;;billi\r\n ng_country\r\n'
                         b'TEL;TYPE=CELL:0606060606\r\n'
                         b'TEL;TYPE=FAX:0505050505\r\nFN:George Abitbol\r\nN:Abitbol;George;;;\r\n'
                         b'TEL;TYPE=WORK:0404040404\r\nURL:www.aaa.fr\r\nEND:VCARD\r\n',
                         response.content
                        )
