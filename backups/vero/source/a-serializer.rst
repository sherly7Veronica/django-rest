assets.serializers
-----------------------

.. automodule:: assets.serializers
    :members:
    :undoc-members:
    :show-inheritance:

import random

from rest_framework import serializers

from assets.models import Assets, LDBEvent, LDBTracking, FreightCarrier


class AssetsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assets
        fields = (
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
        )

class AssetsPostContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assets
        fields = (
            'id',
        )


class AssetsListSerializer(serializers.ModelSerializer):
    dynamic_table = serializers.CharField(source='dynamic_table.table_name')

    class Meta:
        model = Assets
        fields = (
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
        )
        # extra_kwargs = {
        #     'dynamic_table': {'source': 'dynamic_table.table_name'}
        # }


class LDBEventSerializer(serializers.ModelSerializer):
    css_selector = serializers.SerializerMethodField ( 'get_random_number' )

    class Meta:
        model = LDBEvent
        fields = (
            'time',
            'details',
            'particulars' ,
            'css_selector'
        )

    def get_random_number ( self , instance ):
        return random.randint ( 1 , 3 )


class LDBTrackingSerializer(serializers.ModelSerializer):
    events = LDBEventSerializer(many=True, source='get_ldb_event')

    class Meta:
        model = LDBTracking
        fields = (
            'container_no',
            'events',
        )

class FreightCarrierSerializers(serializers.ModelSerializer):
    class Meta:
        model = FreightCarrier
        fields = (
            'id',
            'sos_id',
            'carrier_code',
            'carrier_name',
            'line_scape_id'
        )

