hubs.serializers
-----------------------

.. automodule:: hubs.serializers
    :members:
    :undoc-members:
    :show-inheritance:

from copy import copy

import googlemaps
from cities_light.models import Country
from django.conf import settings
from rest_framework import serializers

from cp_eav.models import DynamicTable
from cp_qb.models import SubUsers
from cp_qb.subusers_helpers import create_qb_customer_for_billing_address
from hubs.models import Hubs


class HubsSerializer(serializers.ModelSerializer):
    gst = serializers.CharField(max_length=15, required=False, allow_null=True, allow_blank=True, source='get_gst')

    class Meta:
        model = Hubs
        fields = (
            'id',
            'name',
            'address_country',
            'address_lat',
            'address_lng',
            'address_line_1',
            'address_line_11',
            'address_line_2',
            'address_line_3',
            # 'incoming_modes',
            # 'outgoing_modes',
            'stakeholder',
            'dynamic_table',
            'address_state',
            'address_zipcode',
            'gst',
        )
        extra_kwargs = {
            'address_country': {
                'required': True
            }
        }

    def create(self, validated_data):

        if 'get_gst' in validated_data:
            gst = validated_data.pop('get_gst')
        else:
            gst = None

        trade_name = None

        if 'dynamic_table' in validated_data:
            if validated_data['dynamic_table'] is None:
                trade_name = copy(validated_data['name'])
                validated_data = self.set_stk_hub(validated_data)
        else:
            trade_name = copy(validated_data['name'])
            validated_data = self.set_stk_hub(validated_data)

        instance = Hubs.objects.create(**validated_data)

        self.set_lat_lng(instance)

        if instance.stakeholder:
            self.create_subuser(instance, gst, trade_name)

        return instance

    def set_stk_hub(self, validated_data):
        stakeholder = self.context['request'].user.stakeholder

        dynamic_table = None

        if settings.STAKEHOLDER_TYPE[stakeholder.dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_CUSTOMER:
            dynamic_table = DynamicTable.objects.get(table_name=settings.HUB_IDENTIFIERS['FACTORY'])
        elif settings.STAKEHOLDER_TYPE[stakeholder.dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_VENDOR:
            dynamic_table = DynamicTable.objects.get(table_name=settings.HUB_IDENTIFIERS['VENDOR'])

        validated_data['dynamic_table'] = dynamic_table
        validated_data['stakeholder'] = stakeholder
        validated_data['name'] = validated_data['address_line_3']
        return validated_data

    def set_lat_lng(self, instance):
        gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)

        geocode_result = gmaps.geocode('{pincode}, {country_code}'.format(
            pincode=instance.address_zipcode,
            country_code=instance.address_country.code2
        ))

        if len(geocode_result) > 0:
            location = geocode_result[0]["geometry"]['location']
            instance.address_lat, instance.address_lng = location['lat'], location['lng']
            instance.save()

        return None, None

    def create_subuser(self, instance, gst, trade_name):
        parent_ref = instance.stakeholder.quickbooks_customer

        subuser = SubUsers.objects.create(
            parent_stakeholder=instance.stakeholder,
            parent_id=parent_ref,
            display_name=instance.name,
            pincode=instance.address_zipcode,
            place=instance.address_line_3,
            state=instance.address_state,
            address1=instance.address_line_1,
            address2=instance.address_line_2,
            gst=gst,
            hub=instance,
            trade_name=trade_name
        )

        try:
            create_qb_customer_for_billing_address(subuser)
        except Exception as exc:
            pass
        return subuser


class HubsShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hubs
        fields = (
            'id',
            'name',
            'address_country',
            'address_lat',
            'address_lng',
            'address_line_1',
            'address_line_11',
            'address_line_2',
            'address_line_3',
            'stakeholder',
            'dynamic_table',
            'address_state',
            'address_zipcode'
        )


class HubsNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hubs
        fields = (
            'id',
            'name'
        )


class HubsAutoCompleteSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source='address_country.name_ascii')

    class Meta:
        model = Hubs
        fields = (
            "id",
            "name",
            "country",
            "stakeholder"
        )


class HubsPostContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hubs
        fields = (
            'id',
        )


class CitiesLightCountrySerializer(serializers.ModelSerializer):
    mobile_country_code = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = (
            'id',
            'name',
            'mobile_country_code'
        )

    def get_mobile_country_code(self, object):
        return '+' + object.phone
