
stakeholder.models
------------------

.. automodule:: stakeholder.models
    :members:
    :undoc-members:
    :show-inheritance:

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import string

from django.conf import settings
from django.db import models

from users.models import CamelportUser
from utils.helpers import random_string
from utils.models import DateBaseModel

ENTITY_PRIVATE_LIMITED = 0
ENTITY_PUBLIC_LIMITED = 1
ENTITY_PARTNERSHIP = 2
ENTITY_PROPRIETORSHIP = 3
ENTITY_LIMITED_LIABILITY_PARTNERSHIP = 4
ENTITY_ONE_PERSON_COMPANY = 5

ENTITY_CHOICES = (
    (ENTITY_PRIVATE_LIMITED, 'pvtltd'),
    (ENTITY_PUBLIC_LIMITED, 'publtd'),
    (ENTITY_PARTNERSHIP, 'partnership'),
    (ENTITY_PROPRIETORSHIP, 'proprietorship'),
    (ENTITY_LIMITED_LIABILITY_PARTNERSHIP, 'limited__liability_lpartnership'),
    (ENTITY_ONE_PERSON_COMPANY, 'one_person_company')
)

DESIGNATION_DIRECTOR = 0
DESIGNATION_PROPRIETOR = 1
DESIGNATION_PARTNER = 2
DESIGNATION_DESIGNATED_PARTNER = 3
DESIGNATION_OTHER = 4

DESIGNATION_CHOICES = (
    (DESIGNATION_DIRECTOR, 'director'),
    (DESIGNATION_PROPRIETOR, 'proprietor'),
    (DESIGNATION_PARTNER, 'partner'),
    (DESIGNATION_DESIGNATED_PARTNER, 'designated_Partner'),
    (DESIGNATION_OTHER, 'other')
)

ROLE_ADMIN = 0
ROLE_OPERATIONS = 1
ROLE_COMMERCIAL = 2
ROLE_ACCOUNTANT = 3

ROLE_CHOICES = (
    (ROLE_ADMIN, 'admin'),
    (ROLE_OPERATIONS, 'operations'),
    (ROLE_COMMERCIAL, 'commercial'),
    (ROLE_ACCOUNTANT, 'accountant')
)


def doc_upload_file_location(instance, filename):
    return 'stakeholder_docs/{}/{}'.format(str(instance.id), filename)


class Stakeholder(DateBaseModel):
    """
    A Stakeholder is any user (typically an organisation) who plays some role in the
    process
    Stake holder will be the base class for all things related to user
    """
    UNVERIFIED_PLAN = 0
    STARTUP_PLAN = 1
    BUSINESS_PLAN = 2
    ENTERPRISE_PLAN = 3
    PLAN_CHOICES = (
        (UNVERIFIED_PLAN, 'unverified'),
        (STARTUP_PLAN, 'startup'),
        (BUSINESS_PLAN, 'business'),
        (ENTERPRISE_PLAN, 'enterprise')

    )
    user = models.OneToOneField(CamelportUser)
    executive_first_name = models.CharField(max_length=32)
    executive_last_name = models.CharField(max_length=32, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)  # @TODO: validator
    mobile = models.CharField(max_length=20, blank=True, null=True)  # @TODO: validator
    email_verified = models.BooleanField(default=False)
    mobile_verified = models.BooleanField(default=False)
    zendesk_id = models.BigIntegerField(blank=True, null=True)
    razor_pay = models.CharField(max_length=30, blank=True, null=True)
    dynamic_table = models.ForeignKey('cp_eav.DynamicTable', blank=True, null=True)
    quickbooks_customer = models.CharField(max_length=30, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=16, blank=True, null=True)
    helpscout_id = models.IntegerField(blank=True, null=True)

    company_name = models.CharField(max_length=256, null=True, blank=True)
    entity_type = models.IntegerField(choices=ENTITY_CHOICES, null=True, blank=True)
    pan_number = models.CharField(max_length=20, null=True, blank=True)
    iec_code = models.CharField(max_length=256, null=True, blank=True)
    company_address_line_1 = models.TextField(null=True, blank=True)
    company_address_line_2 = models.TextField(null=True, blank=True)
    company_address_line_3 = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=256, null=True, blank=True)
    state = models.CharField(max_length=256, null=True, blank=True)
    country = models.CharField(max_length=256, null=True, blank=True)
    zipcode = models.IntegerField(max_length=20, null=True, blank=True)
    designation = models.IntegerField(choices=DESIGNATION_CHOICES, null=True, blank=True)
    authorization_docs = models.FileField(blank=True, null=True, upload_to=doc_upload_file_location)
    reg_status = models.IntegerField(default=0)
    is_enabled = models.BooleanField(default=False)
    razor_account_number = models.CharField(max_length=20, null=True, blank=True)
    razor_ifsc_code = models.CharField(max_length=15, null=True, blank=True)
    pricing_plan = models.IntegerField(choices=PLAN_CHOICES, default=UNVERIFIED_PLAN)

    def __str__(self):

        l_name = ''
        if self.executive_last_name:
            l_name = self.executive_last_name.encode('utf8', 'ignore')

        f_name = ''
        if self.executive_first_name:
            f_name = self.executive_first_name.encode('utf8', 'ignore')

        return "{} {}".format(l_name,
                              f_name)

    def get_complete_stakeholder_address(self):
        complete_address = "{}, {}, {}".format(self.company_address_line_1, self.company_address_line_2,
                                               self.company_address_line_3)
        return complete_address

    @staticmethod
    def get_fields_list():
        return [
            'id',
            'user',
            'executive_first_name',
            'executive_last_name',
            'phone',
            'mobile',
            'email_verified',
            'mobile_verified',
            'zendesk_id',
            'razor_pay',
            'dynamic_table'
        ]

    def get_eav_values(self):
        return self.eav.get_values_dict()

    def get_stakeholder_type(self):
        return self.dynamic_table.table_name

        # def __init__(self, *args, **kwargs):
        #     kwargs['razor_pay'] = create_virtual_account({'name': '{}'.format(self.user.name),
        #                                                   'email':'{}'.format(self.user.email),
        #                                                   'contact': '{}'.format(self.mobile)})
        #     super(Stakeholder, self).__init__(*args, **kwargs)

    def is_customer(self):
        return settings.STAKEHOLDER_TYPE[self.get_stakeholder_type()] == settings.STAKEHOLDER_TYPE_CUSTOMER

    def get_stakeholder_info(self):
        return self.stakeholderinfo


class GuestStakeholder(DateBaseModel):
    parent_stakeholder = models.ForeignKey('stakeholder.Stakeholder', blank=True, null=True,
                                           related_name='guest_parent_stakeholder')
    child_stakeholder = models.OneToOneField('stakeholder.Stakeholder', blank=True, null=True,
                                             related_name='guest_child_stakeholder')
    name = models.CharField(max_length=120)

    def __str__(self):
        if self.name:
            return str(self.name.encode('utf8', 'ignore'))
        else:
            return ""
        # def __str__(self):
        #     return self.user.name.encode('utf8', 'ignore')


class BusinessEntity(DateBaseModel):
    corporate_identification_number = models.CharField(max_length=50)
    date_of_registration = models.DateField(blank=True, null=True)
    company_name = models.CharField(max_length=200)
    company_status = models.CharField(max_length=100, blank=True, null=True)
    company_class = models.CharField(max_length=50, blank=True, null=True)
    company_category = models.CharField(max_length=100, blank=True, null=True)
    authorized_capital = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    paidup_capital = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    registered_state = models.CharField(max_length=50, blank=True, null=True)
    registrar_of_companies = models.CharField(max_length=200, blank=True, null=True)
    principal_business_activity_as_per_cin = models.CharField(max_length=200, blank=True, null=True)
    registered_office_address = models.CharField(max_length=200, blank=True, null=True)
    sub_category = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        if self.company_name:
            return self.company_name.encode('utf8', 'ignore')
        else:
            return ""


# eav.register(StakeholderCategory)


# class LegalEntity(models.Model, DateMixin):
#     """
#     A Legal entity is a branch or factory or entity to which invoices are raised against
#     A stakeholder may have multiple Legal entities register under him
#     """
#     stakeholder = models.ForeignKey(Stakeholder)
#     name = models.CharField(max_length=128, verbose_name='Legal Entity Name')


class StakeholderInfo(DateBaseModel):
    stakeholder = models.OneToOneField('stakeholder.Stakeholder')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    age_of_company_years = models.IntegerField(blank=True, null=True)
    house_bl = models.BooleanField(default=False)
    response_time_hr = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return str(self.stakeholder.user.email)


def get_session_id():
    session_id = random_string(size=128,
                               chars=string.ascii_uppercase + string.ascii_lowercase + string.digits + string.punctuation)
    return session_id


def get_secret_key():
    secret_key = random_string(size=16,
                               chars=string.ascii_uppercase + string.ascii_lowercase + string.digits + string.punctuation)
    return secret_key

class Session(DateBaseModel):
    stakeholder = models.ForeignKey('stakeholder.Stakeholder')
    expires_on = models.DateTimeField()
    access_timestamp = models.IntegerField(default=0)
    public_key = models.CharField(max_length=128)
    remote_ip = models.CharField(max_length=64)
    session_id = models.CharField(max_length=128, default=get_session_id)
    secret_key = models.CharField(max_length=16, default=get_secret_key)

    def __str__(self):
        return str(self.stakeholder.user.email)


def generate_email_token():
    return random_string(size=128)


class EmailVerifyToken(DateBaseModel):
    stakeholder = models.ForeignKey('stakeholder.Stakeholder')
    token = models.CharField(max_length=128, default=generate_email_token)
