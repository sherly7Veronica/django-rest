quote.models
-----------------------

.. automodule:: quote.models
    :members:
    :undoc-members:
    :show-inheritance:

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.conf import settings
from django.db import connection
from django.db import models
# Create your models here.
from django.db.models import Max
from django.db.models.aggregates import Sum, Count
from django.utils import timezone

from assets.models import Assets
from cp_qb.helpers import get_client
from cp_qb.models import SubUsers
from cp_qb.models import SubUsers
from hubs.models import Hubs
from modes.models import Modes
from quickbooks.cp_erp.subcustomer import CPSubCustomer
from quickbooks.exceptions import AuthorizationException
# from quote import helpers
from quote.sos_helper import LegGenerator
from rates.models import Rates, Charges, Penalty
# from shipment.models import Shipment
from stakeholder.models import Stakeholder
from utils.helpers import random_string
from utils.models import DateBaseModel


def get_quote_number():
    quote_string = 'CPQ-' + random_string()

    while Quote.objects.filter(quote_number=quote_string).count() > 0:
        quote_string = 'CPQ-' + random_string()

    return quote_string


class Quote(DateBaseModel):
    WEIGHT_UNIT_UNDEFINED = 0
    WEIGHT_KG = 1
    WEIGHT_METRIC_TON = 2

    VOLUME_UNIT_UNDEFINED = 0
    VOLUME_CUBIC_FEET = 1
    VOLUME_CUBIC_METERS = 2
    VOLUME_LITRES = 3

    WEIGHT_CHOICES = (
        (WEIGHT_UNIT_UNDEFINED, 'undefined'),
        (WEIGHT_KG, 'kg'),
        (WEIGHT_METRIC_TON, 'ton')
    )

    VOLUME_CHOICES = (
        (VOLUME_UNIT_UNDEFINED, 'undefined'),
        (VOLUME_CUBIC_FEET, 'cubic_feet'),
        (VOLUME_CUBIC_METERS, 'cubic_meters'),
        (VOLUME_LITRES, 'litres')
    )

    FOR_DATETYPE_FACTORY = 1
    FOR_DATETYPE_SOURCE_PORT = 2
    # FOR_DATETYPE_DESTINATION = 3

    FOR_DATETYPE_CHOICES = (
        (FOR_DATETYPE_FACTORY, 'factory'),
        (FOR_DATETYPE_SOURCE_PORT, 'source port'),
        # (FOR_DATETYPE_DESTINATION, 'destination'),
    )
    STATUS_PROCESSING = 0
    STATUS_PARTIALLY_COMPLETED = 500
    STATUS_COMPLETED = 1000
    STATUS_CRITICAL = 9999
    STATUS_LAPSED = 10000

    STATUS_CHOICES = (
        (STATUS_PROCESSING , 'Waiting'),
        (STATUS_PARTIALLY_COMPLETED,'Bids Initiated'),
        (STATUS_COMPLETED,'Proceed'),
        (STATUS_CRITICAL,'Critical'),
        (STATUS_LAPSED,'Lapsed')
    )

    stakeholder = models.ForeignKey(Stakeholder, blank=True, null=True)
    source = models.ForeignKey(Hubs, related_name='sourceHubs')
    destination = models.ForeignKey(Hubs, related_name='destinationHubs')
    asset = models.ForeignKey('assets.Assets', blank=True, null=True)

    for_date = models.DateTimeField()
    for_date_choices = models.IntegerField(choices=FOR_DATETYPE_CHOICES, default=FOR_DATETYPE_FACTORY)
    rate = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    rate_currency = models.CharField(max_length=3, blank=True, null=True)
    weight = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    weight_unit = models.IntegerField(choices=WEIGHT_CHOICES, default=WEIGHT_METRIC_TON)
    stuffing_duration = models.IntegerField(default=24 * 60)
    # volume = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    # volume_unit = models.IntegerField(choices=VOLUME_CHOICES, default=VOLUME_UNIT_UNDEFINED)

    include_cha = models.BooleanField(default=True)
    is_dock_stuffing = models.BooleanField(default=False)

    no_of_containers = models.IntegerField()
    selected_route_num = models.PositiveIntegerField(default=None, blank=True, null=True)
    helpscout_id = models.IntegerField(blank=True, null=True)
    quote_number = models.CharField(max_length=32, unique=True, default=get_quote_number)
    billing_address = models.ForeignKey("cp_qb.SubUsers", null=True, blank=True)
    quickbooks_id = models.IntegerField(blank=True, null=True)
    cargo_description = models.CharField(blank=True, null=True, max_length=256)
    status = models.IntegerField(choices = STATUS_CHOICES,default=STATUS_PROCESSING)

    def __str__(self):
        return '{} : {} - {}'.format(str(self.stakeholder.company_name.encode('utf8', 'ignore')),
                                     str(self.source.name.encode('utf8', 'ignore')),
                                     str(self.destination.name.encode('utf8', 'ignore')))

    def create_quote_sub_sub_customer(self, sub_user_id):
        parent_ref = sub_user_id

        sub_sub_user_data = {"DisplayName": self.id}

        try:
            customer_created = CPSubCustomer().create(get_client(), sub_sub_user_data, parent_ref)
            sub_sub_user = SubUsers.objects.create(parent_id=parent_ref, child_str=json.dumps(customer_created),
                                                   child_id=customer_created['Customer']['Id'])
        except AuthorizationException:
            try:
                customer_created = CPSubCustomer().create(get_client(sync_token_var=True), sub_sub_user_data,
                                                          parent_ref)
                sub_sub_user = SubUsers.objects.create(parent_id=parent_ref, child_str=json.dumps(customer_created),
                                                       child_id=customer_created['Customer']['Id'])
            except:
                pass
        return customer_created['Customer']['Id']

    def get_stakeholder_sub_user(self):
        quickbooks_parent = self.stakeholder.quickbooks_customer
        subusers = SubUsers.objects.filter(parent_id=quickbooks_parent)
        subusers_id = []
        for subuser in subusers:
            subusers_id.append(subuser.id)
        return subusers_id

    def generate_legs(self):
        leg_generator = LegGenerator()

        routes = leg_generator.get_routes(self)  # .source, self.destination, self.for_date, self.for_date_choices,
        # self.stuffing_duration)

        route_num = 1
        for route in routes:
            route_num = leg_generator.create_legs(self, route, self.asset, route_num, self.for_date)

        # legs
        if self.quote_legs.count() == 0:
            pass
            # no_legs_task(
            #     source=self.source.name,
            #     destination=self.destination.name,
            #     shipper_name=self.stakeholder.company_name,
            #     helpscout_id=self.helpscout_id,
            #     quote_number=self.quote_number,
            #     total_containers=self.no_of_containers
            # )

        return

    def get_total_rate_for_quote(self):
        selected_legs = self.get_selected_route_legs()
        total_quote_rate = 0
        for leg in selected_legs:
            total_quote_rate += leg.rate
        return total_quote_rate

    def get_total_rate_for_quote_transportation(self):
        return self.get_confirmed_bookings().filter(
            leg__mode=settings.MODE_IDENTIFIERS['ROAD']
        ).distinct().aggregate(sell_rate=Sum('sell_rate'))['sell_rate']

    def get_quickbooks_line_item_list(self, is_sales=False):

        result = []

        for booking in self.get_confirmed_bookings():
            result.append(booking.get_qb_line_item(is_sales=is_sales))

            # @TODO: add rail bookings

        return result

    def get_quickbooks_line_item_list_estimate(self):

        result = []

        for booking in self.get_confirmed_bookings():
            result.append(booking.get_qb_line_item(is_sales=True))

            # @TODO: add rail bookings

        return result

    def get_total_rate_for_quote_sea_freight(self):
        selected_legs = self.get_selected_route_legs()
        total_quote_rate = 0
        for leg in selected_legs:
            if leg.mode.dynamic_table.table_name == "Ocean":
                total_quote_rate += leg.rate
        return total_quote_rate

    def get_total_mode_types_in_quote(self):
        selected_legs = self.get_selected_route_legs()
        modes_dynamic_table = set()
        for leg in selected_legs:
            modes_dynamic_table.add(leg.mode.dynamic_table.table_name)
        return modes_dynamic_table

    def get_transportation_route(self):
        selected_legs = self.get_selected_route_legs()
        selected_legs_transportation = selected_legs.filter(mode__dynamic_table__table_name="Road").order_by("leg_num")
        transportation_route = []
        transportation_route.append(selected_legs[0].fromHub.name)
        for leg in selected_legs_transportation:
            if leg.mode.dynamic_table.table_name == "Road":
                transportation_route.append(leg.toHub.name)
        return transportation_route

    def get_sea_freight_route(self):
        selected_legs = self.get_selected_route_legs()
        selected_legs_sea_freight = selected_legs.filter(mode__dynamic_table__table_name="Ocean").order_by("leg_num")
        sea_freight_route = []
        sea_freight_route.append(selected_legs_sea_freight[0].fromHub.name)
        for leg in selected_legs:
            if leg.mode.dynamic_table.table_name == "Ocean":
                sea_freight_route.append(leg.toHub.name)
        return sea_freight_route

    def get_legs(self):
        return self.quote_legs.all().order_by('route_num', 'leg_num')

    def get_selected_route_legs(self):
        return self.quote_legs.filter(route_num=self.selected_route_num).order_by('leg_num')

    def get_selected_route_grouped_legs(self):
        route_legs = self.get_selected_route_legs()

        grouped_legs = []
        prev_legs = None

        for leg in route_legs:

            if prev_legs is None:
                prev_legs = {
                    'mode': leg.mode,
                    'legs': [leg],
                    'is_import': leg.is_import
                }
                continue

            if leg.mode == prev_legs['mode']:
                prev_legs.setdefault('legs', []).append(leg)
            else:
                grouped_legs.append(prev_legs)
                prev_legs = {
                    'mode': leg.mode,
                    'legs': [leg],
                    'is_import': leg.is_import
                }

        if prev_legs is not None:
            grouped_legs.append(prev_legs)

        for grouped_leg in grouped_legs:
            hub_list = self.get_hub_list_from_legs(grouped_leg['legs'])
            grouped_leg['hub_list'] = hub_list

        return grouped_legs

    # def get_charges_of_a_hub(self):
    #     grouped_legs = self.get_selected_route_grouped_legs()
    #     hub_list = grouped_legs[0]['hub_list']
    #     charge_list = {}
    #     for i, hub in enumerate(hub_list):
    #         try:
    #             charges = Charges.objects.filter(hub=hub)
    #             total_charge = 0
    #             for charge in charges:
    #                 total_charge += charge.get_total_charge()
    #             charge_list[hub.name + str("_") + str(i)] = total_charge
    #         except:
    #             charge = None
    #             charge_list[hub.name + str("_") + str(i)] = charge
    #     return charge_list

    # def get_charges_of_a_hublist(self):
    #     grouped_legs = self.get_selected_route_grouped_legs()
    #     hub_list = grouped_legs[0]['hub_list']
    #     return hub_list

    def get_hub_list_from_legs(self, legs):
        if len(legs) == 0:
            return []

        hub_list = [legs[0].fromHub, ]

        for leg in legs:
            hub_list.append(leg.toHub)

        return hub_list

    def get_rates(self):
        grouped_legs = self.get_grouped_hub_list()

        for grouped_leg in grouped_legs:
            grouped_leg['rates'] = None
            hub_list = grouped_leg['hub_list']
            charges = Charges.objects.filter(hub__in=grouped_leg['hub_list'])

            if len(grouped_leg['legs']) > 0:
                grouped_leg['rates'] = list(Rates.objects.raw(self.get_rates_query(grouped_leg)))
                grouped_leg['charges'] = Charges.objects.filter(chargeforrate__rate__in=grouped_leg['rates'])
                grouped_leg['penalties'] = Penalty.objects.filter(penaltyforrate__rate__in=grouped_leg['rates'])

        return grouped_legs

    # def get_rates_in_percentile(self):
    #     grouped_legs = self.get_rates()
    #     legs = grouped_legs['legs']
    #     rate_list = []
    #     for leg in legs:
    #         rate_list.append(leg.rate)
    #     max_rate = max(rate_list)
    #     percentile_list = []
    #     for leg in legs:
    #         rate_list.append(legs)
    #     for i in rate_list:
    #         percentile_list.append(((100*rate_list[i])/max_rate))


    def get_vendor_quoted_rate(self, grouped_leg, vendor_id):
        return list(Rates.objects.raw(self.get_vendor_rates_query(grouped_leg, vendor_id)))

    def get_vendor_rates_query(self, grouped_leg, vendor_id):
        return "{rate_query} AND service_provider_id='{vendor_id}' ORDER BY rates.provider_rate".format(
            vendor_id=vendor_id,
            rate_query=self.get_rates_query(grouped_leg)
        )

    def get_vendors_min_rate(self, grouped_leg):
        with connection.cursor() as cursor:
            cursor.execute(self.get_vendors_min_rate_query(grouped_leg))
            row = cursor.fetchone()
        return row[0]

    def is_min_rate(self, rate, grouped_leg):
        return rate.provided_rate == self.get_vendors_min_rate(grouped_leg)

    def get_min_rate_object(self):

        return

    def get_vendors_min_rate_query(self, grouped_leg, rate_type=Rates.RATE_TYPE_SPOT):
        hub_query = ''

        appender = ''
        for index, hub in enumerate(grouped_leg['hub_list']):
            hub_query += """
                        {appender} (
                            havershine(hubs.address_lat, hubs.address_lng, {lat},{lng}) < 20 AND
                            rate_leg.leg_num = {leg_num}
                        )
                    """.format(
                appender=appender,
                lat=hub.address_lat,
                lng=hub.address_lng,
                leg_num=index + 1
            )
            appender = 'OR'

        if self.stakeholder_id:
            stakeholder_id = "'{}'".format(self.stakeholder_id)
        else:
            stakeholder_id = 'null'

        query = """
                    SELECT
                        MIN(convert_currency(provider_rate, provider_rate_currency, 'INR'))
                    FROM
                        rates_rates rates
                    WHERE
                        rates.asset_id = '{asset}' AND
                        rates.mode_id = '{mode}' AND
                        rates.weight <= {weight} AND
                        rates.rate_expiry_date >= '{date}' AND
                        rates.num_assets > rates.used_assets AND
                        rates.rate_type = {rate_type} AND
                        (
                            rates.for_stakeholder_id = {shipper} OR
                            rates.for_stakeholder_id IS NULL
                        ) AND
                        (

                            {num_hubs} = (
                                SELECT
                                    COUNT(*)
                                FROM
                                    rates_rateleg rate_leg,
                                    hubs_hubs hubs
                                WHERE
                                    rate_leg.rate_id = rates.id AND
                                    hubs.id = rate_leg.hub_id AND
                                    (
                                        {hub_list_condition}
                                    )
                            )

                        )
                """.format(
            asset=self.asset.id,
            mode=grouped_leg['mode'].id,
            date=grouped_leg['start_date'] - timezone.timedelta(days=1),
            num_hubs=len(grouped_leg['hub_list']),
            hub_list_condition=hub_query,
            shipper=stakeholder_id,
            weight=self.weight,
            rate_type=rate_type
        )

        return query

    def get_rates_query(self, grouped_leg, rate_type=Rates.RATE_TYPE_SPOT):

        hub_query = ''

        appender = ''
        for index, hub in enumerate(grouped_leg['hub_list']):
            hub_query += """
                {appender} (
                    havershine(hubs.address_lat, hubs.address_lng, {lat},{lng}) < 20 AND
                    rate_leg.leg_num = {leg_num}
                )
            """.format(
                appender=appender,
                lat=hub.address_lat,
                lng=hub.address_lng,
                leg_num=index + 1
            )
            appender = 'OR'

        if self.stakeholder_id:
            stakeholder_id = "'{}'".format(self.stakeholder_id)
        else:
            stakeholder_id = 'null'

        query = """
            SELECT
                *
            FROM
                rates_rates rates
            WHERE
                rates.asset_id = '{asset}' AND
                rates.weight <= {weight} AND
                rates.mode_id = '{mode}' AND
                rates.rate_expiry_date >= '{date}' AND
                rates.num_assets > rates.used_assets AND
                rates.rate_type = {rate_type} AND
                (
                    rates.for_stakeholder_id = {shipper} OR
                    rates.for_stakeholder_id IS NULL
                ) AND
                (

                    {num_hubs} = (
                        SELECT
                            COUNT(*)
                        FROM
                            rates_rateleg rate_leg,
                            hubs_hubs hubs
                        WHERE
                            rate_leg.rate_id = rates.id AND
                            hubs.id = rate_leg.hub_id AND
                            (
                                {hub_list_condition}
                            )
                    )

                )
        """.format(
            asset=self.asset.id,
            mode=grouped_leg['mode'].id,
            date=grouped_leg['legs'][0].start_date - timezone.timedelta(days=1),
            num_hubs=len(grouped_leg['hub_list']),
            hub_list_condition=hub_query,
            shipper=stakeholder_id,
            # weight=self.weight,
            weight=self.weight or 50,
            rate_type=rate_type
        )

        return query

    def get_grouped_hub_list(self, filter_mode=None):
        hub_list_group = []

        for elem in self.get_selected_route_grouped_legs():
            curr_group = {
                'mode': elem['mode'],
                'hub_list': self.get_hub_list_from_legs(elem['legs']),
                'is_import': elem['is_import'],
                'start_date': elem['legs'][0].start_date,
                'legs': elem['legs']
            }

            if filter_mode:
                if not elem['mode'].dynamic_table.table_name == filter_mode:
                    continue

            hub_list_group.append(curr_group)

        return hub_list_group

    def get_hub_list(self):
        return (self.get_hub_list_from_legs(self.get_selected_route_legs()))

    def get_num_routes(self):
        route_num = self.quote_legs.all().aggregate(route_num=Max('route_num'))
        return route_num['route_num']

    def get_confirmed_bookings(self):
        return self.booking_set.filter(

            confirmation_date__isnull=False,
            is_cancelled=False
        )

    def get_unconfirmed_bookings(self):
        return self.booking_set.filter(
            confirmation_date__isnull=True,
            is_cancelled=False,
        )

    def get_selected_bookings(self):
        return self.booking_set.filter(
            confirmation_date__isnull=True,
            is_cancelled=False,
        )

    def get_cancelled_bookings(self):
        return self.booking_set.filter(
            is_cancelled=True
        )

    def is_all_bookings_confirmed(self):
        confirmed_bookings = self.get_confirmed_bookings().aggregate(num_assets=Sum('num_assets'), count=Count('id'))
        return confirmed_bookings['num_assets'] == self.no_of_containers * len(self.get_selected_route_grouped_legs())

    def get_confirmed_booking_of_vendor(self, stakeholder):
        return self.get_confirmed_bookings().filter(service_provider=stakeholder).first()

    def get_involved_vendor_types(self):
        if self.selected_route_num:
            vendor_types = set([])
            for leg in self.get_selected_route_legs():
                curr_vendor_type = settings.MODE_VENDORS[leg.mode.dynamic_table.table_name]
                vendor_types.add(curr_vendor_type)

            return list(vendor_types)

        else:
            raise Exception('Vendor list available only for quotes with selected routes')

    def get_route_str(self):
        if self.selected_route_num:
            selected_route_legs = self.get_selected_route_legs()
            route = [selected_route_legs[0].fromHub.name, ]

            for leg in selected_route_legs:
                route.append(leg.toHub.name)

            return " -> ".join(route)

        else:
            raise Exception('Route string available only for quotes with selected routes')

    def clone_rates(self):

        grouped_legs = self.get_selected_route_grouped_legs()

        queries = []

        for grouped_leg in grouped_legs:
            queries.append(
                self.get_rates_query(grouped_leg, rate_type=Rates.RATE_TYPE_CONTRACT)
            )

        queryset = Rates.objects.raw(
            "\nUNION\n".join(queries)
        )

        cloned_contracts = []

        for rate in list(queryset):
            cloned_contracts.append(rate.clone_contract())

        return cloned_contracts


class Leg(DateBaseModel):
    quote = models.ForeignKey(Quote, null=True, blank=True, related_name='quote_legs')
    mode = models.ForeignKey(Modes)
    asset = models.ForeignKey('assets.Assets', blank=True, null=True)
    fromHub = models.ForeignKey(Hubs, related_name='from_hub_leg')
    toHub = models.ForeignKey(Hubs, related_name='to_hub_leg')

    arrival_date = models.DateTimeField(blank=True, null=True)
    start_date = models.DateTimeField()
    duration = models.PositiveIntegerField(default=60)
    delay = models.PositiveIntegerField(default=0)
    description_text = models.CharField(max_length=256, default='')

    leg_num = models.PositiveIntegerField(default=0)
    route_num = models.PositiveIntegerField(default=0)

    rate = models.PositiveIntegerField(default=0)
    rate_currency = models.CharField(max_length=3, blank=True, null=True)

    is_import = models.NullBooleanField(blank=True, null=True, default=None)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return '{}-{}-{}-{}-{}'.format(self.leg_num, self.route_num, self.fromHub.name, self.toHub.name, self.mode.dynamic_table.table_name)

    def get_end_date(self):
        return self.start_date + timezone.timedelta(minutes=self.duration)
