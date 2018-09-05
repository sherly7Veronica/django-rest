rates.serializer
-----------------------

.. automodule:: rates.serializer
    :members:
    :undoc-members:
    :show-inheritance:

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from assets.serializer import AssetsSerializer
from cp_qb.serializer import QuickbooksTaxesSerializer
from hubs.serializer import HubsShortSerializer, HubsNameSerializer
from modes.models import Modes
from payments.helpers import ExchangeRateHelper
from quote.models import Quote
from rates.models import Rates, ChargeDescription, RateLeg, Charges, AbstractTypeCharges, WinningBids, \
    ContractCharges, AbstractPenalty, Penalty, ChargeForRate, PenaltyForRate
from stakeholder.serializers import StakeholderDetailSerializer


class HubListRetrieveSerializer(serializers.ModelSerializer):
    hub = HubsShortSerializer()

    class Meta:
        model = RateLeg
        fields = (
            'id',
            'hub',
            'leg_num'
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'required': False
            }
        }


class HubListSerializer(serializers.ModelSerializer):
    class Meta:
        model = RateLeg
        fields = (
            'id',
            'hub',
            'leg_num'
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'required': False
            }
        }


class HubListNestedSerializer(serializers.ModelSerializer):
    hub = HubsShortSerializer()

    class Meta:
        model = RateLeg
        fields = (
            'id',
            'hub',
            'leg_num'
        )
        extra_kwargs = {
            'id': {
                'read_only': False,
                'required': False
            }
        }


class ChargesShortSerializer(serializers.ModelSerializer):
    hub = HubsNameSerializer(read_only=True)

    class Meta:
        model = Charges
        fields = (
            'id',
            'charge',
            'tax',
            # 'tax_description',
            'hub',
            'charge_currency',
        )


class BidPageAbChargesSerializer(serializers.ModelSerializer):
    hub = HubsNameSerializer(read_only=True)
    tax = QuickbooksTaxesSerializer(read_only=True)
    class Meta:
        model = AbstractTypeCharges
        fields = (
            'id',
            'charge',
            'tax',
            'description',
            'hub',
            'charge_currency',
        )

        extra_kwargs = {
            'id': {
                'read_only': False,
            }
        }


class BidPageAbChargesPostSerializer(serializers.ModelSerializer):
    hub = HubsNameSerializer(read_only=True)

    class Meta:
        model = AbstractTypeCharges
        fields = (
            'id',
            'charge',
            'tax',
            # 'tax_description',
            'hub',
            'charge_currency',
        )

        extra_kwargs = {
            'id': {
                'read_only': False,
            }
        }


####
class BidPageAbChargesTaxSerializer(serializers.ModelSerializer):
    hub = HubsNameSerializer(read_only=True)
    tax = QuickbooksTaxesSerializer(read_only=True)

    class Meta:
        model = AbstractTypeCharges
        fields = (
            'id',
            'charge',
            'tax',
            'description',
            'hub',
            'charge_currency',
        )

        extra_kwargs = {
            'id': {
                'read_only': False,
            }
        }


####

class BidPageChargesSerializer(serializers.ModelSerializer):
    hub = HubsNameSerializer(read_only=True)

    class Meta:
        model = Charges
        fields = (
            'id',
            'charge',
            'description',
            'tax',
            # 'tax_description',
            'hub',
            'charge_currency',
        )

        extra_kwargs = {
            'id': {
                'read_only': False,
            }
        }

        def get_id(self, instance):
            return instance.abstract_charge.id


class BidPageAbPenaltySerializer(serializers.ModelSerializer):
    tax = QuickbooksTaxesSerializer(read_only=True)
    class Meta:
        model = AbstractPenalty
        fields = (
            'id',
            'penalty',
            'tax',
            'description',
            'penalty_type',
            'penalty_currency',
            'tax_currency',
        )

        extra_kwargs = {
            'id': {
                'read_only': False,
            }
        }


class BidPageAbPenaltyPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbstractPenalty
        fields = (
            'id',
            'penalty',
            'description',
            'tax',
            # 'tax_description',
            'penalty_type',
            'penalty_currency',
            'tax_currency',
        )

        extra_kwargs = {
            'id': {
                'read_only': False,
            }
        }
####
class BidPageAbPenaltyTaxSerializer(serializers.ModelSerializer):
    tax = QuickbooksTaxesSerializer(read_only=True)

    class Meta:
        model = AbstractPenalty
        fields = (
            'id',
            'penalty',
            'tax',
            'description',
            'penalty_type',
            'penalty_currency',
            'tax_currency',
        )

        extra_kwargs = {
            'id': {
                'read_only': False,
            }
        }


####

class BidPagePenaltySerializer(serializers.ModelSerializer):
    description = serializers.CharField(source='abstract_penalty.description', read_only=True)

    class Meta:
        model = Penalty
        fields = (
            'id',
            'penalty',
            'tax',
            'description',
            # 'tax_description',
            'penalty_type',
            'penalty_currency',
            'tax_currency',
        )

        extra_kwargs = {
            'id': {
                'read_only': False,
            }
        }

        def get_id(self, instance):
            return instance.abstract_penalty.id


class PenaltyShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Penalty
        fields = (
            'penalty',
            'tax',
            # 'tax_description',
            'penalty_type',
            'penalty_currency',
            'tax_currency',
        )


class AbstractPenaltySerializer(serializers.ModelSerializer):
    class Meta:
        model = AbstractPenalty
        fields = (
            'id',
            'penalty',
            'tax',
            'stakeholder_type',
            'for_abtask',
            # 'tax_description',
            'penalty_type',
            'penalty_currency',
            'tax_currency',
            'mark_up',
        )


class RatesSerializer(serializers.ModelSerializer):
    charges = BidPageAbChargesPostSerializer(many=True, source='get_charges')
    penalties = BidPageAbPenaltyPostSerializer(many=True, source='get_penalties', write_only=True)
    hub_list = HubListSerializer(many=True, source='get_rate_legs', write_only=True)

    class Meta:
        model = Rates
        fields = (
            'id',
            'is_return',
            'provider_rate',
            'provided_rate',
            'tax',
            # 'tax_description',
            'mode',
            'asset',
            'rate_for_date',
            'rate_type',
            'service_provider',
            'for_stakeholder',
            'rate_expiry_date',
            'hub_list',
            'num_assets',
            'weight',
            'tax_currency',
            'provider_rate_currency',
            'provided_rate_currency',
            'charges',
            'penalties',
            'is_import',
            'is_cancelled'
        )

    def create(self, validated_data):
        hub_lists = validated_data.pop('get_rate_legs')
        ab_charges_data = validated_data.pop('get_charges')
        ab_penalties_data = validated_data.pop('get_penalties')

        validated_data['mode'] = Modes.objects.filter(dynamic_table__table_name=settings.VENDOR_MODES[
            self.context['stakeholder'].dynamic_table.table_name]).first()

        if 'rate_type' in validated_data:
            if validated_data['rate_type'] == Rates.RATE_TYPE_SPOT:
                validated_data['rate_expiry_date'] = validated_data['rate_for_date'] + timezone.timedelta(days=7)

        if settings.STAKEHOLDER_TYPE[
            self.context['request'].user.stakeholder.dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_VENDOR:
            validated_data['service_provider_id'] = self.context['request'].user.stakeholder.id

        validated_data['provided_rate'] = validated_data['provider_rate']
        validated_data['provided_rate_currency'] = validated_data['provider_rate_currency']
        rate=Rates.objects.create (tax_id='4d1e7975-8c0c-4f03-91c9-afae63a936af', **validated_data)

        WinningBids.update_winning_bids(rate)

        for hub_list in hub_lists:
            RateLeg.objects.create(
                rate=rate,
                **hub_list
            )

        stakeholder = self.context['stakeholder']

        ab_charges_dict = {str(x["id"]): x for x in ab_charges_data}
        ab_penalties_dict = {str(x["id"]): x for x in ab_penalties_data}

        for ab_charge in AbstractTypeCharges.objects.filter(  # @TODO: convert to a single sql statement
                pk__in=ab_charges_dict.keys()
        ):
            curr_ab_charge_data = ab_charges_dict[str(ab_charge.id)]

            charge = ab_charge.create_charge(
                created_by=stakeholder,
                charge=curr_ab_charge_data['charge'],
                tax=curr_ab_charge_data['tax'],
                charge_currency=curr_ab_charge_data['charge_currency']
            )
            ChargeForRate.objects.create(
                rate=rate,
                charge=charge
            )

        for ab_penalty in AbstractPenalty.objects.filter(  # @TODO: convert to a single sql statement
                pk__in=[x['id'] for x in ab_penalties_data]
        ):
            curr_ab_penalty_data = ab_penalties_dict[str(ab_penalty.id)]

            penalty = ab_penalty.create_penalty(
                penalty=curr_ab_penalty_data['penalty'],
                tax=curr_ab_penalty_data['tax'],
                penalty_currency=curr_ab_penalty_data['penalty_currency'],
                tax_currency=curr_ab_penalty_data['tax_currency']
            )
            PenaltyForRate.objects.create(
                rate=rate,
                penalty=penalty
            )
        return rate

    def update(self, instance, validated_data):
        hub_lists = validated_data.pop('get_rate_legs')
        ab_charges_data = validated_data.pop('get_charges')
        ab_penalties_data = validated_data.pop('get_penalties')

        validated_data['provided_rate'] = validated_data['provider_rate']
        validated_data['provided_rate_currency'] = validated_data['provider_rate_currency']

        rate = instance
        for key, value in validated_data.iteritems():
            setattr(rate, key, value)

        rate.save()

        rate_leg_list = RateLeg.objects.filter(rate=rate)

        rate_leg_ids = []

        for hub_list in hub_lists:
            if 'id' in hub_list:
                rate_leg_ids.append(hub_list['id'])
                rate_leg = rate_leg_list.get(pk=hub_list['id'])
                for key in hub_list:
                    setattr(rate_leg, key, hub_list[key])
                rate_leg.save()
            else:
                rate_leg = RateLeg.objects.create(
                    rate=rate,
                    **hub_list
                )
                rate_leg_ids.append(rate_leg.id)

        rate_leg_list.exclude(id__in=rate_leg_ids).delete()

        WinningBids.update_winning_bids(rate)

        #####

        stakeholder = self.context['stakeholder']

        ab_charges_dict = {str(x["id"]): x for x in ab_charges_data}
        ab_penalties_dict = {str(x["id"]): x for x in ab_penalties_data}

        Charges.objects.filter(
            abstract_charge__pk__in=ab_charges_dict.keys(),
            chargeforrate__rate=rate
        ).delete()

        for ab_charge in AbstractTypeCharges.objects.filter(  # @TODO: convert to a single sql statement
                pk__in=ab_charges_dict.keys()
        ):
            curr_ab_charge_data = ab_charges_dict[str(ab_charge.id)]

            charge = ab_charge.create_charge(
                created_by=stakeholder,
                charge=curr_ab_charge_data['charge'],
                tax=curr_ab_charge_data['tax'],
                charge_currency=curr_ab_charge_data['charge_currency']
            )

            ChargeForRate.objects.create(
                rate=rate,
                charge=charge
            )

        Penalty.objects.filter(
            abstract_penalty__pk__in=ab_penalties_dict.keys(),
            penaltyforrate__rate=rate
        ).delete()
        for ab_penalty in AbstractPenalty.objects.filter(  # @TODO: convert to a single sql statement
                pk__in=[str(x['id']) for x in ab_penalties_data]
        ):
            curr_ab_penalty_data = ab_penalties_dict[str(ab_penalty.id)]

            penalty = ab_penalty.create_penalty(
                penalty=curr_ab_penalty_data['penalty'],
                tax=curr_ab_penalty_data['tax'],
                penalty_currency=curr_ab_penalty_data['penalty_currency'],
                tax_currency=curr_ab_penalty_data['tax_currency']
            )
            PenaltyForRate.objects.create(
                rate=rate,
                penalty=penalty
            )

        return rate


class ContractsSerializer(serializers.ModelSerializer):
    charges = BidPageAbChargesSerializer(many=True, source='get_charges')
    penalties = BidPageAbPenaltySerializer(many=True, source='get_penalties')
    hub_list = HubListNestedSerializer(many=True, source='get_rate_legs')
    asset = AssetsSerializer()

    class Meta:
        model = Rates
        fields = (
            'id',
            'is_return',
            'provider_rate',
            'provided_rate',
            'tax',
            # 'tax_description',
            'mode',
            'asset',
            'rate_for_date',
            'rate_type',
            'service_provider',
            'for_stakeholder',
            'rate_expiry_date',
            'hub_list',
            'num_assets',
            'weight',
            'tax_currency',
            'provider_rate_currency',
            'provided_rate_currency',
            'charges',
            'penalties',
            'is_import',
            'is_cancelled'
        )


# class ShipmentRate(serializers.ModelSerializer):
#     class Meta:
#         model = Rates
#         fields = (
#             'id',
#             'is_return',
#             'rate',
#             'rate_for_date',
#             'rate_type',
#             'rate_expiry_date',
#             'for_leg'
#         )
#
#     def validate_leg(self, leg_id):
#         try:
#             leg = ShipmentLeg.objects.get(pk=leg_id)
#         except ShipmentLeg.DoesNotExist:
#             raise serializers.ValidationError('Leg does exist')
#
#         return leg
#
#     def create(self, validated_data):
#         validated_data['stakeholder'] = self.context['request'].user.stakeholder
#         rate = Rates.objects.create(**validated_data)
#         return rate


class ChargeDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargeDescription
        fields = (
            'code',
            'description'

        )


# class PenaltySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Penalty
#         fields = (
#             'penalty',
#             'stakeholder',
#             'for_abtask',
#             'tax',
#             'tax_description',
#             'penalty_type',
#             'penalty_currency',
#             'tax_currency',
#         )
#
#
# class AbstractTaskPenaltiesRUDSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Penalty
#         fields = (
#             'penalty',
#             'stakeholder',
#             'for_abtask',
#             'tax',
#             'tax_description',
#             'penalty_type',
#             'penalty_currency',
#             'tax_currency',
#         )


class RatesDetailedSerializer(serializers.ModelSerializer):
    hub_list = HubListRetrieveSerializer(many=True, source='get_rate_legs')
    service_provider = StakeholderDetailSerializer()
    charges = BidPageAbChargesSerializer(many=True, source='get_charges')
    penalties = BidPageAbPenaltySerializer(many=True, source='get_penalties')
    total_charge = serializers.DecimalField(max_digits=16, decimal_places=2, source='get_total_charge')

    class Meta:
        model = Rates
        fields = (
            'id',
            'is_return',
            'provider_rate',
            'provided_rate',
            'tax',
            # 'tax_description',
            'mode',
            'asset',
            'weight',
            'num_assets',
            'used_assets',
            'rate_for_date',
            'rate_type',
            'service_provider',
            'for_stakeholder',
            'rate_expiry_date',
            'hub_list',
            'tax_currency',
            'provider_rate_currency',
            'provided_rate_currency',
            'charges',
            'penalties',
            'total_charge',
            'is_cancelled'
        )


class ChargesLCSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charges
        fields = (
            'charge',
            'tax',
            # 'tax_description',
            'charge_for_date',
            'mode',
            'asset',
            'charge_type',
            # 'stakeholder',
            'payee_type',
            'payer_type',
            'description',
            'hub',
            'charge_currency',
            'tax_currency',
            'mark_up',
            'created_by',
            'abstract_charge',
        )


# class AbstractChargesSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = AbstractTypeCharges
#         fields = (
#             'id',
#             'charge',
#             'tax',
#             'tax_description',
#             'charge_for_date',
#             'mode',
#             'asset',
#             'charge_type',
#             'payee_type',
#             'payer_type',
#             'description',
#             'hub',
#             'charge_currency',
#             'tax_currency',
#         )
#
#     def to_representation(self, instance):
#         result = super(AbstractChargesSerializer, self).to_representation(instance)
#         if instance.hub:
#             result['hub'] = instance.hub.name
#         else:
#             result['hub'] = None
#
#         return result


class ChargesSerializer(serializers.ModelSerializer):
    # total_charge = serializers.SerializerMethodField('get_total_charge')

    class Meta:
        model = Charges
        fields = (
            'charge',
            'tax',
            # 'tax_description',
            'charge_for_date',
            'mode',
            'asset',
            'charge_type',
            'stakeholder',
            'payee_type',
            'payer_type',
            'description',
            'hub',
            'get_total_charge',
            'charge_currency',
            'tax_currency',
            'mark_up',
            'created_by',
            'abstract_charge',
        )


class WinningBidsSerializer(serializers.ModelSerializer):
    rate = RatesSerializer()

    class Meta:
        model = WinningBids
        fields = (
            'id',
            'rate'
        )


class AbstractTypeChargesSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbstractTypeCharges
        fields = (
            'id',
            'charge',
            'tax',
            # 'tax_description',
            'charge_for_date',
            'mode',
            'asset',
            'charge_type',
            'payee_type',
            'payer_type',
            'description',
            'hub',
            'charge_currency',
            'tax_currency',
            'mark_up',
        )

    def to_representation(self, instance):
        data = super(AbstractTypeChargesSerializer, self).to_representation(instance)

        to_currency = self.context.get('to_currency', 'INR')
        converted_rate= ExchangeRateHelper.convert_currency(instance.charge_currency,to_currency,instance.charge)

        data['charge'] =converted_rate
        data['charge_currency'] = to_currency
        return data


class RateBidSerializer(serializers.ModelSerializer):
    charges = BidPageAbChargesSerializer(many=True)
    penalties = BidPageAbPenaltySerializer(many=True)
    hub_list = HubListSerializer(many=True, source='get_rate_legs')

    class Meta:
        model = Rates
        fields = (
            'id',
            'is_return',
            'provider_rate',
            'provided_rate',
            'tax',
            # 'tax_description',
            'mode',
            'asset',
            'rate_for_date',
            'rate_type',
            'service_provider',
            'for_stakeholder',
            'rate_expiry_date',
            'hub_list',
            'num_assets',
            'weight',
            'tax_currency',
            'provider_rate_currency',
            'provided_rate_currency',
            'charges',
            'penalties',
            'is_cancelled'
        )

    def get_charges(self):
        return Charges.objects.filter(chargeforrate__rate=self.instance)

    def get_penalties(self):
        return Penalty.objects.filter(penaltyforrate__rate=self.instance)

    def create(self, validated_data):
        return


class ContractChargesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractCharges
        fields = (
            'id',
            'charge',
            'tax',
            # 'tax_description',
            'charge_for_date',
            'mode',
            'asset',
            'charge_type',
            # 'stakeholder',
            'payee',
            'payer',
            'rate',
            'description',
            'hub',
            'charge_currency',
            'tax_currency',
        )


class ContractRateSerializer(serializers.ModelSerializer):
    charges = BidPageAbChargesSerializer()

    # penalties = AbstractPenaltySerializer(many=True)

    class Meta:
        model = Rates
        fields = (
            'id',
            'is_return',
            'provider_rate',
            'provided_rate',
            'tax',
            # 'tax_description',
            'mode',
            'asset',
            'rate_for_date',
            'rate_type',
            'service_provider',
            'for_stakeholder',
            'rate_expiry_date',
            'hub_list',
            'num_assets',
            'weight',
            'tax_currency',
            'provider_rate_currency',
            'provided_rate_currency',
            'charges',
            'is_cancelled',
            # 'penalties',
        )


class VendorBidChargesPenaltyRetrieveSerializer(serializers.ModelSerializer):
    latest_charges = serializers.SerializerMethodField()
    charges = serializers.SerializerMethodField()
    latest_penalties = serializers.SerializerMethodField()
    penalties = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = (
            'latest_charges',
            'charges',
            'latest_penalties',
            'penalties'
        )

    def get_latest_charges(self, instance):
        queryset = AbstractTypeCharges.objects.filter(
            child_charge__appliedcharges__booking__service_provider=self.context['stakeholder'],
            child_charge__appliedcharges__booking__legs__in=instance.get_selected_route_legs(),
        ).distinct()

        return BidPageAbChargesTaxSerializer(queryset, many=True).data

    def get_charges(self, instance):
        hub_list = instance.get_hub_list()

        show_for_stk = ''
        if self.context['stakeholder'].dynamic_table.table_name == settings.STAKEHOLDER_IDENTIFIERS['SHIPPER']:
            show_for_stk = Charges.SHOW_FOR_STAKEHOLDER_SHIPPER
        elif self.context['stakeholder'].dynamic_table.table_name == settings.STAKEHOLDER_IDENTIFIERS['SHIPPING_LINE']:
            show_for_stk = Charges.SHOW_FOR_STAKEHOLDER_FORWARDER
        elif self.context['stakeholder'].dynamic_table.table_name == settings.STAKEHOLDER_IDENTIFIERS['TRUCKER']:
            show_for_stk = Charges.SHOW_FOR_STAKEHOLDER_TRANSPORTER

        query_set = AbstractTypeCharges.objects.filter(hub__in=hub_list, show_for_stakeholder=show_for_stk).distinct()
        return BidPageAbChargesTaxSerializer(query_set, many=True).data

    def get_latest_penalties(self, instance):

        query_set = AbstractPenalty.objects.none()

        if settings.STAKEHOLDER_TYPE[
            self.context['stakeholder'].dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_CUSTOMER:

            query_set = AbstractPenalty.objects.filter(
                child_penalty__penalty_cp_booking__cp_booking__quote__stakeholder=self.context['stakeholder']
            ).distinct()

        elif settings.STAKEHOLDER_TYPE[
            self.context['stakeholder'].dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_VENDOR:

            query_set = AbstractPenalty.objects.filter(
                child_penalty__penalty_booking__booking__service_provider=self.context['stakeholder']
            ).distinct()

        return BidPageAbPenaltyTaxSerializer(query_set, many=True).data

    def get_penalties(self, instance):
        query_set = AbstractPenalty.objects.filter(
            stakeholder_type=self.context['stakeholder'].dynamic_table
        )

        return BidPageAbPenaltyTaxSerializer(query_set, many=True).data


class VendorBidChargesPenaltyUpdateSerializer(VendorBidChargesPenaltyRetrieveSerializer):
    class Meta:
        model = Quote
        fields = (
            'latest_charges',
            'charges',
            'latest_penalties',
            'penalties'
        )

    def get_latest_charges(self, instance):
        queryset = Charges.objects.filter(
            chargeforrate__rate=self.context['rate']
        ).distinct()

        return BidPageChargesSerializer(queryset, many=True).data

    def get_latest_penalties(self, instance):

        query_set = Penalty.objects.none()

        if settings.STAKEHOLDER_TYPE[
            self.context['stakeholder'].dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_CUSTOMER:

            query_set = Penalty.objects.filter(
                penaltyforrate__rate=self.context['rate']
            ).distinct()

        elif settings.STAKEHOLDER_TYPE[
            self.context['stakeholder'].dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_VENDOR:

            query_set = Penalty.objects.filter(
                penaltyforrate__rate=self.context['rate']
            ).distinct()

        return BidPagePenaltySerializer(query_set, many=True).data
