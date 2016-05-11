# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.forms import widgets, models
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from cmsplugin_cascade.fields import PartialFormField
from cmsplugin_cascade.models import CascadePage


class SectionForm(models.ModelForm):
    def clean_glossary(self):
        glossary = self.cleaned_data['glossary']
        if self.check_unique_element_id(self.instance, glossary['element_id']) is False:
            msg = _("The element ID `{element_id}` is not unique for this page.")
            raise ValidationError(msg.format(**glossary))
        return glossary

    @classmethod
    def check_unique_element_id(cls, instance, element_id):
        """
        Check for uniqueness of the given element_id for the current page.
        Return None if instance is not yet associated with a page.
        """
        try:
            element_ids = instance.page.cascadepage.glossary.get('element_ids', {})
        except ObjectDoesNotExist:
            pass
        else:
            element_ids[str(instance.pk)] = element_id
            return len(element_ids) == len(set(element_ids.values()))


class SectionMixin(object):
    def get_form(self, request, obj=None, **kwargs):
        glossary_fields = list(kwargs.pop('glossary_fields', self.glossary_fields))
        glossary_fields.append(PartialFormField('element_id',
            widgets.TextInput(),
            label=_("Element ID"),
            help_text=_("A unique identifier for this element.")
        ))
        kwargs.update(form=SectionForm, glossary_fields=glossary_fields)
        return super(SectionMixin, self).get_form(request, obj, **kwargs)

    @classmethod
    def get_identifier(cls, instance):
        identifier = super(SectionMixin, cls).get_identifier(instance)
        element_id = instance.glossary.get('element_id')
        if element_id:
            return format_html('{0} ID: <em>{1}</em>', identifier, element_id)
        return identifier

    def save_model(self, request, obj, form, change):
        super(SectionMixin, self).save_model(request, obj, form, change)
        CascadePage.assure_relation(obj.page)
        element_id = obj.glossary['element_id']
        if not change:
            # when adding a new element, `element_id` can not be validated for uniqueness
            postfix = 0
            while form.check_unique_element_id(obj, element_id) is False:
                postfix += 1
                element_id = '{element_id}_{0}'.format(postfix, **obj.glossary)
            if postfix:
                obj.glossary['element_id'] = element_id
                obj.save()

        obj.page.cascadepage.glossary.setdefault('element_ids', {})
        obj.page.cascadepage.glossary['element_ids'][str(obj.pk)] = element_id
        obj.page.cascadepage.save()
