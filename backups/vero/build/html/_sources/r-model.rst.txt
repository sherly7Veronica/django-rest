rates.models
-----------------------

.. automodule:: rates.model
    :members:
    :undoc-members:
    :show-inheritance:

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from copy import copy

from django.db import models, connection
# from django.db.models import Sum
from django.utils import timezone

# from booking.urls import booking_patterns
from cp_qb.models import QuickbooksServices
from payments.helpers import ExchangeRateHelper
from utils.models import DateBaseModel


class ChargeDescription(DateBaseModel):
    code = models.CharField(unique=True, max_length=8)
    description = models.CharField(max_length=1024)

    def __str__(self):
        return str(self.description.encode('utf8', 'ignore'))


class Rates(DateBaseModel):
    RATE_TYPE_SPOT = 0
    RATE_TYPE_CONTRACT = 1

    RATE_TYPE_CHOICES = (
        (RATE_TYPE_SPOT, 'spot'),
        (RATE_TYPE_CONTRACT, 'contract')
    )
    is_return = models.BooleanField(default=False)
    provider_rate = models.PositiveIntegerField(verbose_name='Purchase Rate')
    provider_rate_currency = models.CharField(max_length=3, blank=True, null=True)
    provided_rate = models.PositiveIntegerField(blank=True, null=True, default=None, verbose_name='Sell Rate')
    provided_rate_currency = models.CharField(max_length=3, blank=True, null=True)
    tax = models.ForeignKey("cp_qb.QuickbooksTaxes", blank=True, null=True)
    # tax_description = models.CharField(max_length=128, blank=True, null=True)
    mode = models.ForeignKey('modes.Modes', blank=True, null=True)
    asset = models.ForeignKey('assets.Assets', blank=True, null=True)
    weight = models.PositiveIntegerField(default=20)
    num_assets = models.PositiveIntegerField(default=1)
    used_assets = models.PositiveIntegerField(default=0)
    rate_for_date = models.DateTimeField(default=timezone.now)
    rate_type = models.IntegerField(default=RATE_TYPE_SPOT, choices=RATE_TYPE_CHOICES)
    service_provider = models.ForeignKey('stakeholder.Stakeholder', related_name='rate_service_provider',
                                         blank=True, null=True)
    for_stakeholder = models.ForeignKey('stakeholder.Stakeholder', related_name='rate_for_stakeholder',
                                        blank=True, null=True, default=None)

    rate_expiry_date = models.DateTimeField(blank=True, null=True)
    hub_list = models.ManyToManyField('hubs.Hubs', through='rates.RateLeg')
    tax_currency = models.CharField(max_length=3, blank=True, null=True)
    is_import = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False, blank=True)

    def __str__(self):
        return str(self.service_provider.user.email)

    def get_unquoted_legs(self):
        return None

    def get_rate_legs(self):
        return RateLeg.objects.filter(rate=self).order_by('leg_num')

    def get_charges(self):
        return Charges.objects.filter(chargeforrate__rate=self)

    # def get_total_charge(self):
    #     return self.get_charges().aggregate(charge=Sum('charge'))['charge']

    def get_total_charge(self):
        charge_value=0
        charges = self.get_charges()
        for charge in charges:
            converted_charge = ExchangeRateHelper.convert_currency(charge.charge_currency,self.provider_rate_currency,charge.charge)
            if charge.is_atomic:
                charge_value += converted_charge / self.num_assets
            else:
                charge_value += converted_charge
        return charge_value



    def get_penalties(self):
        return Penalty.objects.filter(penaltyforrate__rate=self)

    def clone_contract(self):
        c_rate = Rates.objects.create(
            is_return=self.is_return,
            provider_rate=self.provider_rate,
            provider_rate_currency=self.provider_rate_currency,
            provided_rate=self.provided_rate,
            provided_rate_currency=self.provided_rate_currency,
            tax=self.tax,
            # tax_description=self.tax_description,
            mode=self.mode,
            asset=self.asset,
            weight=self.weight,
            num_assets=self.num_assets,
            used_assets=self.used_assets,
            rate_for_date=self.rate_for_date,
            rate_type=self.RATE_TYPE_SPOT,
            service_provider=self.service_provider,
            for_stakeholder=self.for_stakeholder,
            rate_expiry_date=self.rate_expiry_date,
            tax_currency=self.tax_currency,
            is_import=self.is_import,

        )

        for rate_leg in self.rateleg_set.all():
            RateLeg.objects.create(
                rate=c_rate,
                hub=rate_leg.hub,
                leg_num=rate_leg.leg_num
            )

        return c_rate




class RateLeg(DateBaseModel):
    rate = models.ForeignKey('rates.Rates')
    hub = models.ForeignKey('hubs.Hubs')
    leg_num = models.PositiveIntegerField(default=0)

    def __str__(self):
        return '{}-{}'.format(str(self.rate.service_provider.user.email), str(self.hub.name))


class AbstractTypeCharges(DateBaseModel):
    CHARGE_TYPE_SPOT = 0
    CHARGE_TYPE_CONTRACT = 1

    CHARGE_TYPE_CHOICES = (
        (CHARGE_TYPE_SPOT, 'spot'),
        (CHARGE_TYPE_CONTRACT, 'contract')
    )

    STAKEHOLDER_TYPE_SHIPPER = 0
    STAKEHOLDER_TYPE_VENDOR = 1
    STAKEHOLDER_TYPE_HUBOWNER = 2

    STAKEHOLDER_TYPE_CHOICES = (
        (STAKEHOLDER_TYPE_SHIPPER, 'shipper'),
        (STAKEHOLDER_TYPE_VENDOR, 'vendor'),
        (STAKEHOLDER_TYPE_HUBOWNER, 'hubowner')
    )
    SHOW_FOR_STAKEHOLDER_SHIPPER = 0
    SHOW_FOR_STAKEHOLDER_TRANSPORTER = 1
    SHOW_FOR_STAKEHOLDER_HUBOWNER = 2
    SHOW_FOR_STAKEHOLDER_FORWARDER = 3

    SHOW_FOR_STAKEHOLDER_CHOICES = (
        (SHOW_FOR_STAKEHOLDER_SHIPPER, 'shipper'),
        (SHOW_FOR_STAKEHOLDER_TRANSPORTER, 'transporter'),
        (SHOW_FOR_STAKEHOLDER_HUBOWNER, 'hubowner'),
        (SHOW_FOR_STAKEHOLDER_FORWARDER, 'forwarder')
    )

    charge = models.PositiveIntegerField()
    tax = models.ForeignKey("cp_qb.QuickbooksTaxes", blank=True, null=True)
    # tax_description = models.CharField(max_length=128)
    charge_for_date = models.DateField(max_length=10)
    mode = models.ForeignKey('modes.Modes', blank=True, null=True)
    asset = models.ForeignKey('assets.Assets', blank=True, null=True)
    charge_type = models.IntegerField(default=CHARGE_TYPE_SPOT, choices=CHARGE_TYPE_CHOICES)
    payee_type = models.IntegerField(default=STAKEHOLDER_TYPE_SHIPPER, choices=STAKEHOLDER_TYPE_CHOICES)
    payer_type = models.IntegerField(default=STAKEHOLDER_TYPE_SHIPPER, choices=STAKEHOLDER_TYPE_CHOICES)
    description = models.CharField(max_length=512)
    hub = models.ForeignKey('hubs.Hubs', blank=True, null=True)
    charge_currency = models.CharField(max_length=3, blank=True, null=True)
    tax_currency = models.CharField(max_length=3, blank=True, null=True)
    mark_up = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_atomic = models.BooleanField(default=False)
    show_for_stakeholder = models.IntegerField(default=SHOW_FOR_STAKEHOLDER_TRANSPORTER,
                                               choices=SHOW_FOR_STAKEHOLDER_CHOICES)

    def create_charge(self, created_by, charge, tax, charge_currency=None, tax_currency=None):
        return self._create_charges(
            created_by=created_by,
            charge=charge,
            tax=tax,
            charge_currency=charge_currency or self.charge_currency,
            tax_currency=tax_currency or self.tax_currency
        )

    def _create_charges(self, created_by, charge, tax, charge_currency, tax_currency):
        return Charges.objects.create(
            created_by=created_by,
            charge=charge,
            tax=tax,
            # tax_description=self.tax_description,
            charge_for_date=self.charge_for_date,
            mode=self.mode,
            asset=self.asset,
            charge_type=self.charge_type,
            payee_type=self.payee_type,
            payer_type=self.payer_type,
            description=self.description,
            hub=self.hub,
            charge_currency=charge_currency,
            tax_currency=tax_currency,
            mark_up=self.mark_up,
            abstract_charge=self,
            is_atomic=self.is_atomic,
            show_for_stakeholder = self.show_for_stakeholder
        )

    def __str__(self):
        return str(self.description.encode('utf8', 'ignore'))


class Charges(DateBaseModel):
    CHARGE_TYPE_SPOT = 0
    CHARGE_TYPE_CONTRACT = 1

    CHARGE_TYPE_CHOICES = (
        (CHARGE_TYPE_SPOT, 'spot'),
        (CHARGE_TYPE_CONTRACT, 'contract')
    )

    STAKEHOLDER_TYPE_SHIPPER = 0
    STAKEHOLDER_TYPE_VENDOR = 1
    STAKEHOLDER_TYPE_HUBOWNER = 2

    STAKEHOLDER_TYPE_CHOICES = (
        (STAKEHOLDER_TYPE_SHIPPER, 'shipper'),
        (STAKEHOLDER_TYPE_VENDOR, 'vendor'),
        (STAKEHOLDER_TYPE_HUBOWNER, 'hubowner')
    )
    SHOW_FOR_STAKEHOLDER_SHIPPER = 0
    SHOW_FOR_STAKEHOLDER_TRANSPORTER=1
    SHOW_FOR_STAKEHOLDER_HUBOWNER = 2
    SHOW_FOR_STAKEHOLDER_FORWARDER = 3

    SHOW_FOR_STAKEHOLDER_CHOICES = (
        (SHOW_FOR_STAKEHOLDER_SHIPPER, 'shipper'),
        (SHOW_FOR_STAKEHOLDER_TRANSPORTER, 'transporter'),
        (SHOW_FOR_STAKEHOLDER_HUBOWNER, 'hubowner'),
        (SHOW_FOR_STAKEHOLDER_FORWARDER, 'forwarder')
    )

    charge = models.PositiveIntegerField()
    tax = models.ForeignKey("cp_qb.QuickbooksTaxes", blank=True, null=True)
    # tax_description = models.CharField(max_length=128)
    charge_for_date = models.DateField(max_length=10)
    mode = models.ForeignKey('modes.Modes', blank=True, null=True)
    asset = models.ForeignKey('assets.Assets', blank=True, null=True)
    charge_type = models.IntegerField(default=CHARGE_TYPE_SPOT, choices=CHARGE_TYPE_CHOICES)
    payee_type = models.IntegerField(default=STAKEHOLDER_TYPE_SHIPPER, choices=STAKEHOLDER_TYPE_CHOICES)
    payer_type = models.IntegerField(default=STAKEHOLDER_TYPE_SHIPPER, choices=STAKEHOLDER_TYPE_CHOICES)
    description = models.CharField(max_length=512)
    hub = models.ForeignKey('hubs.Hubs', blank=True, null=True)
    charge_currency = models.CharField(max_length=3, blank=True, null=True)
    tax_currency = models.CharField(max_length=3, blank=True, null=True)
    mark_up = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_by = models.ForeignKey('stakeholder.Stakeholder', blank=True, null=True)
    abstract_charge = models.ForeignKey(AbstractTypeCharges, related_name='child_charge')
    is_atomic = models.BooleanField(default=False)
    show_for_stakeholder = models.IntegerField(default=SHOW_FOR_STAKEHOLDER_TRANSPORTER,choices=SHOW_FOR_STAKEHOLDER_CHOICES)

    def create_applied_charge(self, cp_booking, booking):
        return AppliedCharges.objects.create(
            booking=booking,
            cp_booking=cp_booking,
            charge=self,
            payee=self.get_stakeholder(
                cp_booking=cp_booking,
                booking=booking,
                hub=self.hub,
                type=self.payee_type
            ),
            payer=self.get_stakeholder(
                cp_booking=cp_booking,
                booking=booking,
                hub=self.hub,
                type=self.payer_type
            )

        )

    def charge_currency_conversion(self):
        to_currecy_code = 'INR'
        converted_currency = ExchangeRateHelper.convert_currency(self.charge_currency, to_currecy_code,self.charge)
        return converted_currency

    def __str__(self):
        return str(self.description.encode('utf8', 'ignore'))

    def get_total_charge(self):
        total_charge = self.charge_currency_conversion() * (1 + (float(self.tax.tax) / 100))
        return total_charge

    def get_receivable_charge(self):
        return (self.charge_currency_conversion() * (1 + (self.mark_up / 100))) * (1 + (self.tax.tax / 100))

    def get_stakeholder(self, cp_booking, booking, hub, type):
        if type == AbstractTypeCharges.STAKEHOLDER_TYPE_SHIPPER:
            return cp_booking.quote.stakeholder
        elif type == AbstractTypeCharges.STAKEHOLDER_TYPE_VENDOR:
            return booking.service_provider
        elif type == AbstractTypeCharges.STAKEHOLDER_TYPE_HUBOWNER:
            return hub.stakeholder
        else:
            return None

    def get_purchase_tax_amount(self):
        return float(self.charge_currency_conversion() * (self.tax.tax / 100))
        #return float (self.charge * (self.tax.tax / 100))

    def get_purchase_total_amount(self):
        return float(self.charge_currency_conversion())

    def get_sell_rate(self):
        return float(self.charge_currency_conversion() * float((1 + (self.mark_up / 100))))

    def get_sell_tax_amount(self):
        return float(self.get_sell_rate() * (float(self.tax.tax) / 100))

    def get_sell_total_amount(self):
        return float(self.get_sell_rate())


class ChargeForRate(DateBaseModel):
    charge = models.ForeignKey(Charges, on_delete=models.CASCADE)
    rate = models.ForeignKey(Rates)

    def create_charge_for_booking(self, booking):
        return ChargeForBooking.objects.create(charge=self.charge, booking=booking)

    def __str__(self):
        return str(self.charge.description)


class ChargeForBooking(DateBaseModel):
    charge = models.ForeignKey(Charges)
    booking = models.ForeignKey('booking.Booking', related_name='charge_booking')

    def create_applied_charge(self, cp_booking):
        return self.charge.create_applied_charge(
            cp_booking=cp_booking,
            booking=self.booking
        )

    def __str__(self):
        return str(self.charge.description)


class AppliedCharges(DateBaseModel):
    charge = models.OneToOneField(Charges)
    booking = models.ForeignKey('booking.Booking')
    cp_booking = models.ForeignKey('booking.CPBooking')
    payer = models.ForeignKey('stakeholder.Stakeholder', related_name='payer_applied_charge')
    payee = models.ForeignKey('stakeholder.Stakeholder', related_name='payee_applied_charge')

    def __str__(self):
        return str(self.charge.description)

    def get_applied_charge_amount(self):
        if self.charge.is_atomic:
            curr_charge_amount = self.charge.charge
        else:
            curr_charge_amount = self.charge.charge * self.booking.num_assets
        return curr_charge_amount

    def get_applied_charge_purchase_tax(self):
        return (1 + (float(self.charge.tax.tax) / 100))

    def get_applied_charge_purchase_total_amount(self):
        gross_amount = float(self.get_applied_charge_amount() * self.get_applied_charge_purchase_tax())
        return gross_amount

    def get_applied_charge_sell_rate(self):
        return (1+ (float(self.charge.mark_up) / 100))

    def get_applied_charge_sell_rate_tax_amount(self):
        sell_rate_amount = float(self.get_applied_charge_amount() * self.get_applied_charge_sell_rate() * (float(self.charge.tax.tax)/100))
        return sell_rate_amount

    def get_applied_charge_sell_total_amount(self):
        total_sell_rate_amount = float(self.get_applied_charge_sell_rate() + self.get_applied_charge_sell_rate_tax_amount())
        return total_sell_rate_amount

    def get_receivable_applied_charge(self):
        receivable_amount = float(self.get_applied_charge_amount() * self.get_applied_charge_sell_rate() * self.get_applied_charge_purchase_tax())
        return receivable_amount

    def get_qb_bill_line_item(self):
        item_detail = "ItemBasedExpenseLineDetail"

        qty = 1

        # amt = self.charge.get_sell_total_amount()
        amt = self.charge.get_purchase_total_amount()

        unit_price = copy(amt)

        if self.charge.is_atomic:
            unit_price = self.charge.charge / self.booking.num_assets

        line_entry = {
            "Amount": amt * qty,
            "Description": self.charge.description,
            "DetailType": item_detail,
            item_detail: {
                'MarkupInfo': {
                    'Percent': str(float(self.charge.mark_up))
                },
                "CustomerRef": {
                    "value": self.cp_booking.quote.quickbooks_id,
                },
                "ItemRef": {
                    "value": QuickbooksServices.objects.get(name='Charges').quickbook_id
                },
                "Qty": qty,
                "UnitPrice": unit_price,
                "TaxCodeRef": {
                    "value": str(self.charge.tax.quickbook_id)
                },
                "BillableStatus": "Billable"
            },
        }

        if self.charge.tax:
            line_entry[item_detail]['TaxCodeRef'] = {
                "value": str(self.charge.tax.quickbook_id)
            }

        return line_entry

    def get_qb_line_item(self, sell=True, is_sales=False):

        if is_sales:
            item_detail = "SalesItemLineDetail"
        else:
            item_detail = "ItemBasedExpenseLineDetail"

        qty = 1

        if sell:
            amt = self.charge.get_sell_total_amount()
        else:
            amt = self.charge.get_purchase_total_amount()

        if not self.charge.is_atomic:
            qty = self.booking.num_assets

        line_entry = {
            "Amount": amt * qty,
            "Description": self.charge.description,
            "DetailType": item_detail,
            item_detail: {
                "ItemRef": {
                    "value": QuickbooksServices.objects.get(name='Charges').quickbook_id
                },
                "Qty": qty,
                "UnitPrice": amt,
                "TaxCodeRef": {
                    "value": str(self.charge.tax.quickbook_id)
                }
            },
        }

        if self.charge.tax:
            line_entry[item_detail]['TaxCodeRef'] = {
                "value": str(self.charge.tax.quickbook_id)
            }

        return line_entry


####
class AbstractPenalty(DateBaseModel):
    PENALTY_TYPE_FLAT = 0
    PENALTY_TYPE_PER_HOUR = 1
    PENALTY_TYPE_PER_DAY = 2
    PENALTY_TYPE_PER_WEEK = 3
    PENALTY_TYPE_PER_MONTH = 4

    PENALTY_TYPE_CHOICES = (
        (PENALTY_TYPE_FLAT, 'flat'),
        (PENALTY_TYPE_PER_HOUR, 'hour'),
        (PENALTY_TYPE_PER_DAY, 'day'),
        (PENALTY_TYPE_PER_WEEK, 'week'),
        (PENALTY_TYPE_PER_MONTH, 'month')
    )
    penalty = models.PositiveIntegerField()
    stakeholder_type = models.ForeignKey('cp_eav.DynamicTable')
    for_abtask = models.ForeignKey('task.AbstractTask', blank=True, null=True)
    tax = models.ForeignKey("cp_qb.QuickbooksTaxes", blank=True, null=True)
    # tax_description = models.CharField(max_length=128)
    penalty_type = models.IntegerField(default=PENALTY_TYPE_FLAT, choices=PENALTY_TYPE_CHOICES)
    penalty_currency = models.CharField(max_length=3, blank=True, null=True)
    tax_currency = models.CharField(max_length=3, blank=True, null=True)
    mark_up = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    description = models.CharField(max_length=512, blank=True, null=True)

    def __str__(self):
        return str(self.description.encode('utf8', 'ignore'))

    def create_penalty(self, penalty, tax, penalty_currency=None, tax_currency=None):
        return self._create_penalty(
            penalty=penalty,
            tax=tax,
            penalty_currency=penalty_currency or self.penalty_currency,
            tax_currency=tax_currency or self.tax_currency
        )

    def _create_penalty(self, penalty, tax, penalty_currency, tax_currency):
        return Penalty.objects.create(
            penalty=penalty,
            stakeholder_type=self.stakeholder_type,
            for_abtask=self.for_abtask,
            tax_currency=tax_currency,
            tax=tax,
            penalty_type=self.penalty_type,
            penalty_currency=penalty_currency,
            mark_up=self.mark_up,
            # tax_description=self.tax_description,
            abstract_penalty=self
        )


class Penalty(DateBaseModel):
    PENALTY_TYPE_FLAT = 0
    PENALTY_TYPE_PER_HOUR = 1
    PENALTY_TYPE_PER_DAY = 2
    PENALTY_TYPE_PER_WEEK = 3
    PENALTY_TYPE_PER_MONTH = 4

    PENALTY_TYPE_CHOICES = (
        (PENALTY_TYPE_FLAT, 'flat'),
        (PENALTY_TYPE_PER_HOUR, 'hour'),
        (PENALTY_TYPE_PER_DAY, 'day'),
        (PENALTY_TYPE_PER_WEEK, 'week'),
        (PENALTY_TYPE_PER_MONTH, 'month')
    )
    penalty = models.PositiveIntegerField()
    stakeholder_type = models.ForeignKey('cp_eav.DynamicTable')
    for_abtask = models.ForeignKey('task.AbstractTask', blank=True, null=True)
    # for_abtask = models.ManyToManyField('task.AbstractTask')
    tax = models.ForeignKey("cp_qb.QuickbooksTaxes", blank=True, null=True)
    # tax_description = models.CharField(max_length=128)
    penalty_type = models.IntegerField(default=PENALTY_TYPE_FLAT, choices=PENALTY_TYPE_CHOICES)
    penalty_currency = models.CharField(max_length=3, blank=True, null=True)
    tax_currency = models.CharField(max_length=3, blank=True, null=True)
    mark_up = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    abstract_penalty = models.ForeignKey(AbstractPenalty, related_name='child_penalty')

    def __str__(self):
        return str(self.abstract_penalty.description)

    def create_applied_penalty(self, booking, cp_booking):
        return AppliedPenalties.objects.create(
            penalty=self,
            booking=booking,
            cp_booking=cp_booking
        )

    def create_penalty_for_booking(self, booking):
        return PenaltyForBooking.objects.create(
            penalty=self,
            booking=booking
        )

    def create_penalty_for_cp_booking(self, cp_booking):
        return PenaltyForCPBooking.objects.create(
            penalty=self,
            cp_booking=cp_booking
        )

    def get_purchase_tax_amount(self):
        return self.penalty * (self.tax.tax / 100)

    def get_purchase_total_amount(self):
        return self.penalty + self.get_purchase_tax_amount()

    def get_sell_rate(self):
        return self.penalty * (1 + (self.mark_up / 100))

    def get_sell_tax_amount(self):
        return self.get_sell_rate() * (self.tax.tax / 100)

    def get_sell_total_amount(self):
        return self.get_sell_rate() + self.get_purchase_tax_amount()


class PenaltyForRate(DateBaseModel):
    penalty = models.ForeignKey(Penalty, on_delete=models.CASCADE)
    rate = models.ForeignKey(Rates)

    def __str__(self):
        return str(self.penalty.abstract_penalty.description)


class PenaltyForCPBooking(DateBaseModel):
    penalty = models.ForeignKey(Penalty, related_name='penalty_cp_booking')
    cp_booking = models.ForeignKey('booking.CPBooking')

    def __str__(self):
        return str(self.penalty.abstract_penalty.description)

    def create_applied_penalty(self, booking):
        self.penalty.create_applied_penalty(
            booking=booking,
            cp_booking=self.cp_booking
        )

### Not to be used
class PenaltyForBooking(DateBaseModel):
    penalty = models.ForeignKey(Penalty, related_name='penalty_booking')
    booking = models.ForeignKey('booking.Booking')

    def __str__(self):
        return str(self.penalty.abstract_penalty.description)


class AppliedPenalties(DateBaseModel):
    penalty = models.OneToOneField(Penalty)
    booking = models.ForeignKey('booking.Booking')
    cp_booking = models.ForeignKey('booking.CPBooking')

    def __str__(self):
        return str(self.penalty.abstract_penalty.description)


class WinningBids(DateBaseModel):
    rate = models.ForeignKey('rates.Rates')

    def __str__(self):
        return str(self.rate.service_provider.user.email)

    @staticmethod
    def update_winning_bids(rate_instance):
        hub_condition = ''

        for rate_leg in rate_instance.rateleg_set.all():
            hub_condition += """
                AND havershine({lat}, {lng}, h.address_lat, h.address_lng) < 20
            """.format(
                lat=rate_leg.hub.address_lat,
                lng=rate_leg.hub.address_lng
            )

        delete_query = """
        DELETE
        FROM rates_winningbids
        WHERE
        rate_id IN (
            SELECT r.id FROM rates_rates r
            INNER JOIN rates_rateleg leg
             ON leg.rate_id = r.id
            INNER JOIN hubs_hubs h
              ON h.id = leg.hub_id
            WHERE 1=1
              {hub_condition}
            GROUP BY
              r.id
            HAVING
              {num_hubs} = COUNT(leg.hub_id)
        )
        """.format(
            num_hubs=rate_instance.rateleg_set.all().count(),
            hub_condition=hub_condition
        )

        with connection.cursor() as cursor:
            cursor.execute(delete_query)

        WinningBids.objects.create(rate=rate_instance)


class ContractCharges(DateBaseModel):
    CHARGE_TYPE_SPOT = 0
    CHARGE_TYPE_CONTRACT = 1

    CHARGE_TYPE_CHOICES = (
        (CHARGE_TYPE_SPOT, 'spot'),
        (CHARGE_TYPE_CONTRACT, 'contract')
    )

    charge = models.PositiveIntegerField()
    tax = models.ForeignKey("cp_qb.QuickbooksTaxes", blank=True, null=True)
    # tax_description = models.CharField(max_length=128)
    charge_for_date = models.DateField(max_length=10)
    mode = models.ForeignKey('modes.Modes', blank=True, null=True)
    asset = models.ForeignKey('assets.Assets', blank=True, null=True)
    charge_type = models.IntegerField(default=CHARGE_TYPE_SPOT, choices=CHARGE_TYPE_CHOICES)
    payee = models.ForeignKey('stakeholder.Stakeholder', related_name='payee_contract_charge')
    payer = models.ForeignKey('stakeholder.Stakeholder', related_name='payer_contract_charge')
    rate = models.ForeignKey(Rates, blank=True, null=True)
    description = models.ForeignKey(ChargeDescription)
    hub = models.ForeignKey('hubs.Hubs', blank=True, null=True)
    charge_currency = models.CharField(max_length=3, blank=True, null=True)
    tax_currency = models.CharField(max_length=3, blank=True, null=True)

    def __str__(self):
        return str(self.description)

    def get_total_charge(self):
        total_charge = self.charge * (1 + (float(self.tax) / 100))
        return total_charge
