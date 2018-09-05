hubs.models
-----------------------

.. automodule:: hubs.models
    :members:
    :undoc-members:
    :show-inheritance:


        # -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
import eav
from modes.models import Modes
from stakeholder.models import Stakeholder
from utils.models import DateBaseModel


class Hubs(DateBaseModel):
    IS_CHARGE_UNIT_TIME_HOUR = 24
    IS_CHARGE_UNIT_TIME_DAY = 1
    IS_CHARGE_UNIT_TIME_WEEK = 1 / 7
    IS_CHARGE_UNIT_TIME_MONTH = 1 / 30.5

    IS_CHARGE_UNIT_TIME_CHOICES = (
        (IS_CHARGE_UNIT_TIME_HOUR, 'per hour'),
        (IS_CHARGE_UNIT_TIME_DAY, 'per day'),
        (IS_CHARGE_UNIT_TIME_WEEK, 'per week'),
        (IS_CHARGE_UNIT_TIME_MONTH, 'per month')
    )

    name = models.CharField(max_length=64)
    address_line_1 = models.CharField(max_length=256, blank=True, null=True)
    address_line_11 = models.CharField(max_length=256, blank=True, null=True)
    address_line_2 = models.CharField(max_length=256, blank=True, null=True)
    address_line_3 = models.CharField(max_length=256, blank=True, null=True)
    address_country = models.ForeignKey('cities_light.Country', blank=True, null=True)  # @TODO: remove blank, null
    address_lat = models.DecimalField(max_digits=22, decimal_places=18, null=True, blank=True)
    address_lng = models.DecimalField(max_digits=22, decimal_places=18, null=True, blank=True)
    incoming_modes = models.ManyToManyField(Modes, related_name='outgoing_hub')
    outgoing_modes = models.ManyToManyField(Modes, related_name='incoming_hub')
    stakeholder = models.ForeignKey(Stakeholder, blank=True, null=True)
    dynamic_table = models.ForeignKey('cp_eav.DynamicTable', blank=True, null=True)
    address_state = models.CharField(max_length=256, blank=True, null=True)
    address_zipcode = models.CharField(max_length=10, blank=True, null=True)
    code = models.CharField(max_length=8, blank=True, null=True)
    linescape_id = models.IntegerField(blank=True, null=True)
    sharp_id = models.IntegerField(blank=True, null=True)
    alternative_names = models.CharField(blank=True, default="", max_length=2048)
    geo_id = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return "{}".format(self.name.encode('utf8', 'ignore'))

    @staticmethod
    def get_fields_list():
        return [
            'id',
            'name'
            'is_cha',
            'holding_charge',
            'is_charge_unit_time',
            'address_line_1',
            'incoming_modes',
            'outgoing_modes',
            'stakeholder',
            'dynamic_table'
            'address_state',
            'address_zipcode'
        ]

    def get_eav_values(self):
        return self.eav.get_values_dict()

    def get_lat_lng(self):
        lat_lng = (self.address_lat, self.address_lng)
        return lat_lng

    def get_gst(self):
        try:
            return self.subusers.gst
        except:
            return None


eav.register(Hubs)
