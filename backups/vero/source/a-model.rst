assets.models
-----------------------

.. automodule:: assets.model
    :members:
    :undoc-members:
    :show-inheritance:

# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import unicode_literals

from django.db import models

import cp_eav
import eav
from cp_eav.models import DynamicTable
from eav.registry import EavConfig
from utils.models import DateBaseModel
# Create your models here.
from utils.models import DateBaseModel


class Assets(DateBaseModel):
    LENGTH_UNIT_UNDEFINED = 0
    LENGTH_UNIT_M = 1
    LENGTH_UNIT_FT = 2
    LENGTH_UNIT_CM = 3

    LENGTH_CHOICES = (
        (LENGTH_UNIT_UNDEFINED, 'undefined'),
        (LENGTH_UNIT_M, 'metre'),
        (LENGTH_UNIT_CM, 'centimeter'),
        (LENGTH_UNIT_FT, 'feet')
    )

    WEIGHT_UNIT_UNDEFINED = 0
    WEIGHT_UNIT_KG = 1
    WEIGHT_UNIT_POUNDS = 2
    WEIGHT_METRIC_TON = 3

    WEIGHT_CHOICES = (
        (WEIGHT_UNIT_UNDEFINED, 'undefined'),
        (WEIGHT_UNIT_KG, 'kilogram'),
        (WEIGHT_UNIT_POUNDS, 'pounds'),
        (WEIGHT_METRIC_TON, 'metric ton')
    )
    identifier = models.CharField(max_length=32)
    length = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    length_unit = models.IntegerField(choices=LENGTH_CHOICES, default=LENGTH_UNIT_UNDEFINED)
    width = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    width_unit = models.IntegerField(choices=LENGTH_CHOICES, default=LENGTH_UNIT_UNDEFINED)
    height = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    height_unit = models.IntegerField(choices=LENGTH_CHOICES, default=LENGTH_UNIT_UNDEFINED)

    interior_length = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    interior_length_unit = models.IntegerField(choices=LENGTH_CHOICES, default=LENGTH_UNIT_UNDEFINED)
    interior_width = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    interior_width_unit = models.IntegerField(choices=LENGTH_CHOICES, default=LENGTH_UNIT_UNDEFINED)
    interior_height = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    interior_height_unit = models.IntegerField(choices=LENGTH_CHOICES, default=LENGTH_UNIT_UNDEFINED)

    weight = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    weight_unit = models.IntegerField(choices=WEIGHT_CHOICES, default=WEIGHT_UNIT_UNDEFINED)

    is_dimension_constant = models.BooleanField(default=True)
    is_weight_constant = models.BooleanField(default=True)
    dynamic_table = models.ForeignKey(cp_eav.models.DynamicTable, blank=True, null=True)

    @staticmethod
    def get_fields_list():
        return [
            'id',
            'identifier',
            'length',
            'length_unit',
            'width',
            'width_unit',
            'height',
            'height_unit',
            'weight',
            'weight_unit',
            'is_dimension_constant',
            'is_weight_constant',
            'dynamic_table'
        ]

    def get_eav_values(self):
        return self.eav.get_values_dict()

    def __str__(self):
        return str(self.identifier.encode('utf8', 'ignore'))


class MyEavConfigClass(EavConfig):
    manager_attr = 'eav_objects'


eav.register(Assets, MyEavConfigClass)


class LDBTracking(DateBaseModel):
    container_no = models.CharField(max_length=15)

    def get_ldb_event(self):
        return self.ldbevent_set.all()


class LDBEvent(DateBaseModel):
    time = models.DateTimeField()
    details = models.CharField(max_length=256)
    particulars = models.CharField(max_length=256)
    ldb_tracking = models.ForeignKey(LDBTracking)

class FreightCarrier(DateBaseModel):
    sos_id = models.IntegerField()
    carrier_code = models.CharField(max_length=32)
    carrier_name = models.CharField(max_length=512)
    line_scape_id = models.IntegerField()

    def get_logo_url(self):
        return
