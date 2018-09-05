rates.views
-----------------------

.. automodule:: rates.views
    :members:
    :undoc-members:
    :show-inheritance:

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils import timezone
# Create your views here.
from rest_framework import generics
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from camelport import settings
from quote.models import Quote
from rates.models import Rates, Charges, AbstractTypeCharges, ChargeDescription, AbstractPenalty
from rates.serializer import RatesSerializer, ChargeDescriptionSerializer, ChargesLCSerializer, \
    BidPageAbPenaltySerializer, AbstractTypeChargesSerializer, BidPageAbChargesSerializer, \
    VendorBidChargesPenaltyRetrieveSerializer, AbstractPenaltySerializer, VendorBidChargesPenaltyUpdateSerializer, \
    ContractsSerializer, BidPageChargesSerializer
from utils.metadata import CPMeta
from utils.pagination import CamelportPagination, Camelport15Pagination
# Create your views here.
from utils.permissions import VendorOnlyAccessPermission, ShipperOnlyAccessPermission


class RatesListCreateAPIView(generics.ListCreateAPIView):
    pagination_class = CamelportPagination
    metadata_class = CPMeta
    serializer_class = RatesSerializer

    def get_queryset(self):
        return Rates.objects.filter(rate_type=Rates.RATE_TYPE_SPOT, is_cancelled=False)

    def get_serializer_context(self):
        context = super(RatesListCreateAPIView, self).get_serializer_context()
        context['stakeholder'] = self.request.user.stakeholder
        return context


class ContractsListCreateAPIView(generics.ListCreateAPIView):
    pagination_class = Camelport15Pagination
    metadata_class = CPMeta
    serializer_class = ContractsSerializer
    permission_classes = [VendorOnlyAccessPermission, ]

    def get_queryset(self):
        return Rates.objects.filter(rate_type=Rates.RATE_TYPE_CONTRACT, service_provider=self.request.user.stakeholder,
                                    is_cancelled=False)

    def get_serializer_context(self):
        context = super(ContractsListCreateAPIView, self).get_serializer_context()
        context['stakeholder'] = self.request.user.stakeholder
        return context


class RatesRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RatesSerializer

    def get_queryset(self):
        return Rates.objects.all()

    def get_serializer_context(self):
        context = super(RatesRetrieveUpdateDestroyAPIView, self).get_serializer_context()
        context['stakeholder'] = self.request.user.stakeholder
        return context


##################################################################


class ChargeDescriptionListCreateApiView(generics.ListCreateAPIView):
    pagination_class = CamelportPagination
    metadata_class = CPMeta

    def get_queryset(self):
        return ChargeDescription.objects.all()

    serializer_class = ChargeDescriptionSerializer


class ChargeDescriptionRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        return ChargeDescription.objects.all()


######################################################################


class AbstractTaskPenaltiesRUDAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AbstractPenaltySerializer

    def get_queryset(self):
        # absTask = AbstractTask.objects.get(pk=)
        return AbstractPenalty.objects.filter()
        #     return Penalty.objects.filter(
        #         for_abtask_id=self.kwargs['pk']
        #     )
        #
        # def get_penalty_object(self):
        #         return self.queryset.get(pk=self.kwargs['penalty'])


class RelevantChargeListForQuote(generics.ListAPIView):
    pagination_class = None
    permission_classes = [VendorOnlyAccessPermission, ]
    serializer_class = AbstractTypeChargesSerializer

    def get_queryset(self):
        quote = get_object_or_404(Quote, pk=self.kwargs.get('quote_id', 1))
        hub_list = quote.get_hub_list()
        return AbstractTypeCharges.objects.filter(hub__in=hub_list).distinct()



class RelevantPenaltyList(generics.ListAPIView):
    pagination_class = None
    permission_classes = [IsAuthenticated, ]
    serializer_class = BidPageAbPenaltySerializer

    def get_queryset(self):
        return AbstractPenalty.objects.filter(
            stakeholder_type=self.request.user.stakeholder.dynamic_table
        )


class PenaltyListCreateApiView(generics.ListCreateAPIView):
    pagination_class = None
    metadata_class = CPMeta

    def get_queryset(self):
        return AbstractPenalty.objects.filter(
            stakeholder=self.request.user.stakeholder
        )

    serializer_class = AbstractPenaltySerializer


class PenaltyRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        return AbstractPenalty.objects.all()


class PenaltyList(generics.ListAPIView):
    serializer_class = AbstractPenaltySerializer
    pagination_class = None

    def get_queryset(self):
        return AbstractPenalty.objects.all()


class PenaltyLatest(generics.ListAPIView):
    serializer_class = BidPageAbPenaltySerializer
    pagination_class = None
    permission_classes = [IsAuthenticated, ]

    def get_queryset(self):

        if settings.STAKEHOLDER_TYPE[
            self.request.user.stakeholder.dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_CUSTOMER:

            return AbstractPenalty.objects.filter(
                child_penalty__penalty_cp_booking__cp_booking__quote__stakeholder=self.request.user.stakeholder
            ).distinct()

        elif settings.STAKEHOLDER_TYPE[
            self.request.user.stakeholder.dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_VENDOR:

            return AbstractPenalty.objects.filter(
                child_penalty__penalty_booking__booking__service_provider=self.request.user.stakeholder
            ).distinct()


class ShipperPenaltyLatest(generics.ListAPIView):
    serializer_class = BidPageAbPenaltySerializer
    pagination_class = None
    permission_classes = [IsAuthenticated, ]

    def get_queryset(self):

        if settings.STAKEHOLDER_TYPE[
            self.request.user.stakeholder.dynamic_table.table_name] == settings.STAKEHOLDER_TYPE_CUSTOMER:

            return AbstractPenalty.objects.filter(
                child_penalty__penalty_cp_booking__cp_booking__quote__stakeholder=self.request.user.stakeholder
            ).distinct()

        elif settings.STAKEHOLDER_TYPE[
            self.request.user.stakeholder.dynamic_table.table_name] == settings.STAKEHOLDER_IDENTIFIERS['SHIPPER']:

            return AbstractPenalty.objects.filter(
                child_penalty__penalty_booking__booking__service_provider=self.request.user.stakeholder
            ).distinct()


class ChargesLCApiView(generics.ListCreateAPIView):
    serializer_class = ChargesLCSerializer
    queryset = Charges.objects.all()


class ChargeLatest(generics.ListAPIView):
    serializer_class = BidPageAbChargesSerializer
    pagination_class = None
    permission_classes = [VendorOnlyAccessPermission, ]

    def get_queryset(self):
        return AbstractTypeCharges.objects.filter(
            child_charge__chargeforbooking__booking__service_provider=self.request.user.stakeholder
        )


class ShipperChargeLatest(generics.ListAPIView):
    serializer_class = BidPageAbChargesSerializer
    pagination_class = None
    permission_classes = [ShipperOnlyAccessPermission, ]

    def get_queryset(self):
        return AbstractTypeCharges.objects.filter(
            child_charge__chargeforbooking__booking__service_provider=self.request.user.stakeholder
        )


######################################################################

class AbstractChargesLCApiView(generics.ListCreateAPIView):
    pagination_class = None
    serializer_class = AbstractTypeChargesSerializer
    queryset = AbstractTypeCharges.objects.all()


class AbstractChargeDescriptionRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    pagination_class = None

    def get_queryset(self):
        return AbstractTypeCharges.objects.all()


#####################################################################

class BidStatsApiView(APIView):
    permission_classes = [VendorOnlyAccessPermission, ]

    def get(self, request, *args, **kwargs):
        rates_queryset = Rates.objects.filter(
            service_provider=request.user.stakeholder,
            rate_expiry_date__gte=timezone.now()
        )

        bid_stats = {
            'winning': RatesSerializer(
                rates_queryset.filter(winningbids__isnull=False).order_by('rate_for_date').distinct()[:5],
                many=True
            ).data,
            'losing': RatesSerializer(
                rates_queryset.filter(winningbids__isnull=True).order_by('rate_for_date').distinct()[:5],
                many=True
            ).data
        }

        return Response(bid_stats)


class VendorBidChargesPenaltyRetrieve(generics.RetrieveAPIView):
    pagination_class = None
    serializer_class = VendorBidChargesPenaltyRetrieveSerializer

    def get_queryset(self):
        # return Quote.objects.filter(booking__service_provider=self.request.user.stakeholder).distinct()
        return Quote.objects.all()

    def get_serializer_context(self):
        context = super(VendorBidChargesPenaltyRetrieve, self).get_serializer_context()
        context.update({
            'stakeholder': self.request.user.stakeholder
        })
        return context


class VendorBidUpdateChargesPenaltyRetrieve(generics.RetrieveAPIView):
    pagination_class = None
    serializer_class = VendorBidChargesPenaltyUpdateSerializer

    def __init__(self, **kwargs):
        super(VendorBidUpdateChargesPenaltyRetrieve, self).__init__(**kwargs)
        self.rate_instance = None

    def get_queryset(self):
        # return Quote.objects.filter(booking__service_provider=self.request.user.stakeholder).distinct()
        return Quote.objects.all()

    def get_serializer_context(self):
        context = super(VendorBidUpdateChargesPenaltyRetrieve, self).get_serializer_context()
        self.rate_instance = get_object_or_404(Rates, pk=self.kwargs.get('rate_id', 1))
        context.update({
            'stakeholder': self.request.user.stakeholder,
            'rate': self.rate_instance
        })
        return context


class ChargesAndPenaltiesForHubsListView(generics.ListAPIView):
    pagination_class = None
    serializer_class = BidPageChargesSerializer

    def get_queryset(self):
        hub_ids = self.kwargs.get('hubs').split(',')
        return Charges.objects.filter(abstract_charge__hub__id__in=hub_ids)
