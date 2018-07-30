# -*- coding: utf-8 -*-

try:
    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from .base import _EmailsTestCase, skipIfCustomEmailTemplate, EmailTemplate
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomEmailTemplate
class TemplatesTestCase(_EmailsTestCase):
    def setUp(self):
        self.login()

    def test_createview01(self):  # TODO: test attachments
        url = reverse('emails__create_template')
        self.assertGET200(url)

        name      = 'my_template'
        subject   = 'Insert a joke *here*'
        body      = 'blablabla {{first_name}}'
        body_html = '<p>blablabla {{last_name}}</p>'
        response = self.client.post(url, follow=True,
                                    data={'user':      self.user.pk,
                                          'name':      name,
                                          'subject':   subject,
                                          'body':      body,
                                          'body_html': body_html,
                                         }
                                   )
        self.assertNoFormError(response)

        template = self.get_object_or_fail(EmailTemplate, name=name)
        self.assertEqual(subject,   template.subject)
        self.assertEqual(body,      template.body)
        self.assertEqual(body_html, template.body_html)

        # ----
        response = self.assertGET200(template.get_absolute_url())
        self.assertTemplateUsed(response, 'emails/view_template.html')

    def test_createview02(self):
        "Validation error"
        response = self.assertPOST200(reverse('emails__create_template'), follow=True,
                                      data={'user':      self.user.pk,
                                            'name':      'my_template',
                                            'subject':   'Insert a joke *here*',
                                            'body':      'blablabla {{unexisting_var}}',
                                            'body_html': '<p>blablabla</p> {{foobar_var}}',
                                           }
                                     )

        error_msg = _('The following variables are invalid: %(vars)s')
        self.assertFormError(response, 'form', 'body',
                             error_msg % {'vars': ['unexisting_var']}
                            )
        self.assertFormError(response, 'form', 'body_html',
                             error_msg % {'vars': ['foobar_var']}
                            )

    def test_editview01(self):
        name    = 'my template'
        subject = 'Insert a joke *here*'
        body    = 'blablabla'
        template = EmailTemplate.objects.create(user=self.user, name=name, subject=subject, body=body)

        url = template.get_edit_absolute_url()
        self.assertGET200(url)

        name    = name.title()
        subject = subject.title()
        body    += ' edited'
        response = self.client.post(url, follow=True,
                                    data={'user':    self.user.pk,
                                          'name':    name,
                                          'subject': subject,
                                          'body':    body,
                                         }
                                   )
        self.assertNoFormError(response)

        template = self.refresh(template)
        self.assertEqual(name,    template.name)
        self.assertEqual(subject, template.subject)
        self.assertEqual(body,    template.body)
        self.assertEqual('',      template.body_html)

    def test_listview(self):
        response = self.assertGET200(EmailTemplate.get_lv_absolute_url())

        with self.assertNoException():
            response.context['entities']
