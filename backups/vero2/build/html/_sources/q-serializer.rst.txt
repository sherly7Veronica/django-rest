quote.serializer
-----------------------

.. automodule:: quote.serializer
    :members:
    :undoc-members:
    :show-inheritance:

from django.conf import settings
from rest_framework import serializers

from assets.serializer import AssetsSerializer
from cp_qb.subusers_helpers import create_quote_subuser
from helpscout.customer import HSCustomer
from hubs.serializer import HubsShortSerializer
from modes.models import Modes
from modes.serializer import ModesNameSerializer
from quote.models import Quote, Leg
from rates.serializer import RatesSerializer, RatesDetailedSerializer
from shipment.models import Shipment
from shipment.serializers import ShipmentSerializer
from stakeholder.serializers import StakeholderRegisterSerializer


class LegsSerializer(serializers.ModelSerializer):
    fromHub = HubsShortSerializer()
    toHub = HubsShortSerializer()
    mode = ModesNameSerializer()

    class Meta:
        model = Leg
        fields = (
            'id',
            'mode',
            'fromHub',
            'toHub',
            'leg_num',
            'route_num',
            'start_date',
            'duration',
            'rate',
            'delay',
            'description_text',
            'is_import',
            'rate_currency',
            'is_active',
            'arrival_date'
        )


class RouteSelectionLegSerializer(serializers.ModelSerializer):
    end_date = serializers.DateTimeField()

    class Meta:
        model = Leg
        fields = (
            'id',
            'leg_num',
            'start_date',
            'end_date',
            'delay',
            'is_import',
            'arrival_date'
        )
        extra_kwargs = {
            'id': {
                'read_only': False
            }
        }


class RouteSelectionQuoteSerializer(serializers.ModelSerializer):
    legs = RouteSelectionLegSerializer(many=True, write_only=True)
    route_num = serializers.IntegerField()

    class Meta:
        model = Quote
        fields = (
            'route_num',
            'legs',
            'cargo_description',
        )

    def validate_route_num(self, value):

        if not Leg.objects.filter(quote_id=self.instance.id, route_num=value).count():
            raise serializers.ValidationError('Route does not exists')
        return value

    def update(self, instance, validated_data):
        # @TODO: save changes for future leg generation

        # create shipments
        for i in range(instance.no_of_containers):
            shipment = Shipment.objects.create(
                shipper_quote=instance,
                shipment_num=i + 1
            )

            # create shipment legs
            for leg in validated_data['legs']:

                leg['duration'] = int((leg['end_date'] - leg['start_date']).total_seconds() / 60)
                route_leg = Leg.objects.get(pk=leg['id'])

                for key in leg:
                    setattr(route_leg, key, leg[key])

                route_leg.save()

                if route_leg.fromHub == instance.source:
                    instance.for_date = route_leg.start_date

        instance.selected_route_num = validated_data['route_num']
        # instance.for_date = instance.quote_legs.filter(route_num=validated_data['route_num']).order_by('leg_num').first().start_date
        instance.save()

        instance.clone_rates()

        return instance


class QuoteSerializer(serializers.ModelSerializer):
    legs = LegsSerializer(many=True, source='get_legs', read_only=True)
    num_routes = serializers.IntegerField(source='get_num_routes', read_only=True)
    class Meta:
        model = Quote
        fields = (
            'id',
            'stakeholder',
            'source',
            'destination',
            'asset',
            'for_date',
            'for_date_choices',
            'weight',
            'no_of_containers',
            'include_cha',
            'is_dock_stuffing',
            'stuffing_duration',
            'legs',
            'num_routes',
            'helpscout_id',
            'quote_number',
            'rate_currency',
            'billing_address',
            'quickbooks_id',
            'cargo_description'
        )
        extra_kwargs = {
            "billing_address": {
                "required": False  # <== make True later
            },
            "quickbooks_id": {
                "required": False
            }
        }

    def create(self, validated_data):
        stakeholder = self.context['request'].user.stakeholder
        validated_data['stakeholder_id'] = stakeholder.id
        quote = super(QuoteSerializer, self).create(validated_data=validated_data)

        try:
            response, status = HSCustomer().create_customer({
                'firstName': stakeholder.executive_first_name,
                'lastName': stakeholder.executive_last_name,
                'emails': [
                    {
                        "value": self.context['request'].user.email.replace('@', '+{}@'.format(quote.quote_number)),
                        "location": "work"
                    }
                ],
                'organization': str(stakeholder.id)
            })
            if response:
                quote.helpscout_id = response['id']
                quote.save()
        except Exception as exc:
            pass  # exception_error_message(exc)
        quote.generate_legs()

        try:
            create_quote_subuser(quote)
        except:
            pass
        return quote


class QuoteListSerializer(serializers.ModelSerializer):
    source = HubsShortSerializer()
    destination = HubsShortSerializer()
    stakeholder = StakeholderRegisterSerializer()
    asset = AssetsSerializer()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = (
            'id',
            'stakeholder',
            'source',
            'destination',
            'asset',
            'for_date',
            'for_date_choices',
            'weight',
            'no_of_containers',
            'include_cha',
            'is_dock_stuffing',
            'stuffing_duration',
            'helpscout_id',
            'selected_route_num',
            'quote_number',
            'rate_currency',
            'cargo_description',
            'status'
        )

    def get_status(self,obj):
        rate_legs = obj.get_rates()
        rate_flag = False
        rate_count = True
        count = 0
        for rate_leg in rate_legs:
            number_of_asset = 0
            for num_asset in rate_leg['rates']:
                number_of_asset +=num_asset.num_assets
            if number_of_asset >= obj.no_of_containers:
                rate_flag = True
            if rate_leg['rates']==[]:
                rate_count =False
                count+=1
        if  rate_count==True and rate_flag==True:
            obj.status=Quote.STATUS_COMPLETED
        elif (rate_count==False or rate_flag==False) and count<len(rate_legs):
            obj.status = Quote.STATUS_PARTIALLY_COMPLETED
        elif rate_count == False and rate_flag == False and count==len(rate_legs):
            obj.status = Quote.STATUS_PROCESSING

        return obj.status


class QuoteDetailSerializer(serializers.ModelSerializer):
    shipments = ShipmentSerializer(many=True, read_only=True, source='quote_shipments')

    class Meta:
        model = Quote
        fields = (
            'id',
            'stakeholder',
            'source',
            'destination',
            'asset',
            'rate',
            'for_date',
            'for_date_choices',
            'weight',
            'weight_unit',
            'shipments',
            'no_of_containers',
            'include_cha',
            'is_dock_stuffing',
            'stuffing_duration',
            'quote_number',
            'rate_currency',
            'cargo_description'
        )


class QuoteUnConfirmedBookingDetailSerializer(serializers.ModelSerializer):
    shipments = ShipmentSerializer(many=True, read_only=True, source='quote_shipments')
    source = HubsShortSerializer()
    destination = HubsShortSerializer()

    class Meta:
        model = Quote
        fields = (
            'id',
            'stakeholder',
            'source',
            'destination',
            'asset',
            'rate',
            'for_date',
            'for_date_choices',
            'weight',
            'weight_unit',
            'shipments',
            'no_of_containers',
            'include_cha',
            'is_dock_stuffing',
            'stuffing_duration',
            'quote_number',
            'rate_currency',
            'cargo_description'
        )


class QuoteSelectedRouteLegsSerializer(serializers.ModelSerializer):
    legs = LegsSerializer(many=True, source='get_selected_route_legs', read_only=True)
    num_routes = serializers.IntegerField(source='get_num_routes', read_only=True)

    class Meta:
        model = Quote
        fields = (
            'id',
            'stakeholder',
            'source',
            'destination',
            'asset',
            'for_date',
            'for_date_choices',
            'weight',
            'no_of_containers',
            'include_cha',
            'is_dock_stuffing',
            'stuffing_duration',
            'legs',
            'num_routes',
            'quote_number',
            'rate_currency',
            'cargo_description'
        )


class LegWithNoOfContainersSerializer(serializers.ModelSerializer):
    no_of_containers = QuoteSerializer(many=True, source='get_legs', read_only=True)

    class Meta:
        model = Leg
        fields = (
            'id',
            'mode',
            'asset',
            'fromHub',
            'toHub',
            'start_date',
            'duration',
            'delay',
            'description_text',
            'leg_num',
            'route_num',
            'rate',
            'is_import',
            'rate_currency',
            'is_active',
            'arrival_date'
        )


class QuoteRatesSerializer(serializers.ModelSerializer):
    rate_legs = serializers.SerializerMethodField('quote_rate_leg')
    asset = AssetsSerializer()

    class Meta:
        model = Quote
        fields = (
            'id',
            'stakeholder',
            'source',
            'destination',
            'asset',
            'for_date',
            'for_date_choices',
            'weight',
            'no_of_containers',
            'include_cha',
            'is_dock_stuffing',
            'stuffing_duration',
            'rate_legs',
            'quote_number',
            'rate_currency',
            'cargo_description'
        )

    def quote_rate_leg(self, obj):
        result = []

        rate_legs = obj.get_rates()

        for rate_leg in rate_legs:
            curr_row = {
                'legs': LegsSerializer(rate_leg['legs'], many=True).data,
                'rates': RatesDetailedSerializer(rate_leg['rates'], many=True).data,
            }
            result.append(curr_row)

        return result


class VendorQuoteRequirementListSerializer(serializers.ModelSerializer):
    grouped_legs = serializers.SerializerMethodField('quote_grouped_legs')
    mode = serializers.SerializerMethodField('mode_for_legs')
    asset = AssetsSerializer()

    class Meta:
        model = Quote
        fields = (
            'id',
            'asset',
            'mode',
            'for_date',
            'for_date_choices',
            'weight',
            'no_of_containers',
            'include_cha',
            'is_dock_stuffing',
            'stuffing_duration',
            'grouped_legs',
            'quote_number',
            'rate_currency',
            'cargo_description'
        )

    def quote_grouped_legs(self, obj):
        grouped_legs = obj.get_grouped_hub_list(
            filter_mode=settings.VENDOR_MODES[self.context['request'].user.stakeholder.dynamic_table.table_name]
        )

        result = []

        for grouped_leg in grouped_legs:
            # result.append(HubsShortSerializer(grouped_leg['hub_list'], many=True).data)
            # @TODO: split grouped legs for multinational use case (surface)

            quoted_rates = obj.get_vendor_quoted_rate(
                vendor_id=self.context['request'].user.stakeholder.id,
                grouped_leg=grouped_leg
            )
            quoted_rate = None
            if len(quoted_rates) > 0:
                quoted_rate = RatesSerializer(quoted_rates[0]).data

            curr_obj = {
                'hub_list': HubsShortSerializer(grouped_leg['hub_list'], many=True).data,
                'min_rate': obj.get_vendors_min_rate(grouped_leg),
                'min_rate_currency': 'INR',
                'quoted_rate': quoted_rate,
                'is_import': grouped_leg['is_import'],
                'start_date': grouped_leg['start_date']
            }
            result.append(curr_obj)

        if len(result) > 0:
            return result[0]
        else:
            return None

    def mode_for_legs(self, obj):
        mode_name = settings.VENDOR_MODES[self.context['request'].user.stakeholder.dynamic_table.table_name]
        return {
            'id': Modes.objects.filter(dynamic_table__table_name=mode_name).first().id,
            'name': mode_name
        }