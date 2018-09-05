quote.view
-----------------------

.. automodule:: quote.view
    :members:
    :undoc-members:
    :show-inheritance:

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db.models.aggregates import Count
from django.http import Http404
from django.utils import timezone
from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notification.helpers import NotificationHelper
from notification.models import Notification
from quote import serializers
from quote.metadata import QuoteMeta
from quote.models import Quote, Leg
from stakeholder.models import Stakeholder
from utils.pagination import CamelportPagination, Camelport15Pagination
from utils.permissions import VendorOnlyAccessPermission


class QuoteCreateView(generics.CreateAPIView):
    # pagination_class = CamelportPagination
    """Create Quote by Shipper. Shipping Address(Hub) is compulsory"""
    metadata_class = QuoteMeta
    permission_classes = [IsAuthenticated, ]

    serializer_class = serializers.QuoteSerializer
    queryset = Quote.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        response = serializer.data
        return Response(response, status=status.HTTP_201_CREATED, headers=headers)


class QuoteListView(generics.ListAPIView):
    """Return a list of all the existing quote. """
    pagination_class = CamelportPagination
    metadata_class = QuoteMeta
    permission_classes = [IsAuthenticated, ]

    serializer_class = serializers.QuoteListSerializer

    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        'source__name', 'destination__name', 'quote_number', 'for_date', 'stakeholder__executive_first_name',
        'stakeholder__executive_last_name')
    ordering_fields = ('for_date', 'source__name', 'destination__name')

    def get_queryset(self):
        return Quote.objects.filter(
            stakeholder=self.request.user.stakeholder
        ).annotate(
            cp_booking_count=Count('cpbooking')
        ).filter(
            cp_booking_count=0
        ).filter(
            selected_route_num__isnull=False
        )  # .order_by('-for_date')
    queryset = Quote.objects.all()

    # filter_backends = (filters.DjangoFilterBackend,filters.OrderingFilter)
    # filter_class = QuoteFilter
    # ordering_fields = ('for_date')
    # ordering = ('-for_date')



class QuoteRUDView(generics.RetrieveUpdateDestroyAPIView):
    """
    get: Return a list of all the existing Quote.,
    put: Update quote with given id,
    patch:Update an existing entity only selected field,
    delete: Delete quote with given id.
    """
    serializer_class = serializers.QuoteSerializer

    # permission_classes = [IsAuthenticated, ]
    def get_object(self):
        queryset = self.get_queryset()

        try:
            return queryset.get(
                pk=self.kwargs['pk']
            )
        except:
            pass

        try:
            return queryset.get(
                quote_number=self.kwargs['pk']
            )
        except:
            pass

        raise Http404

    def get_queryset(self):
        return Quote.objects.all()


# class QuoteDetailRetrieveView(generics.RetrieveAPIView):
#     serializer_class = serializers.QuoteDetailSerializer
#     permission_classes = [IsAuthenticated, ]
#
#     def get_object(self):
#         queryset = self.get_queryset()
#
#         try:
#             return queryset.get(
#                 pk=self.kwargs['pk']
#             )
#         except:
#             pass
#
#         try:
#             return queryset.get(
#                 quote_number=self.kwargs['pk']
#             )
#         except:
#             pass
#
#         raise Http404
#
#     def get_queryset(self):
#         return Quote.objects.filter(stakeholder=self.request.user.stakeholder)


class RouteSelectionUpdateView(generics.UpdateAPIView):
    """It shows route(collection of hub) for created quote."""
    serializer_class = serializers.RouteSelectionQuoteSerializer
    permission_classes = [IsAuthenticated, ]

    def get_object(self):
        queryset = self.get_queryset()

        try:
            return queryset.get(
                pk=self.kwargs['pk']
            )
        except queryset.model.DoesNotExist:

            try:
                return queryset.get(
                    quote_number=self.kwargs['pk']
                )
            except queryset.model.DoesNotExist:
                raise Http404

    def get_queryset(self):
        return Quote.objects.filter(stakeholder=self.request.user.stakeholder).filter(selected_route_num=None)

    # queryset = Quote.objects.filter(selected_route_num=None)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        response_serializer = serializers.QuoteSelectedRouteLegsSerializer(instance=instance)

        self.generate_vendor_notifications(instance=instance)

        self.generate_customer_notification(instance=instance)

        return Response({})

    def generate_vendor_notifications(self, instance):
        sender_list = Stakeholder.objects.filter(
            dynamic_table__table_name__in=instance.get_involved_vendor_types(),
            whatsapp_number__isnull=False  # @TODO: delete this filter
        )

        for_date_str = instance.for_date.strftime("%d/%m/%Y")

        msg_short = '{source} - {destination} : {date}'.format(
            source=instance.source.code or instance.source.name,
            destination=instance.destination.code or instance.destination.name,
            date=for_date_str
        )

        msg_long = '{num_assets} containers of {asset_type} required for route :\n{route}\n\nFor Date: {date}'.format(
            num_assets=instance.no_of_containers,
            asset_type="{feet}' {identifier}".format(
                identifier=instance.asset.identifier,
                feet=instance.asset.length
            ),
            route=instance.get_route_str(),
            date=for_date_str
        )

        NotificationHelper.send_notification(
            sender_list=sender_list,
            title='New Quote Request',
            message_long=msg_long,
            message_short=msg_short,
            object_id=str (instance.id),
            notification_type=Notification.NOTIFICATION_TYPE_VENDOR_BID,
            send_email=True
        )

    def generate_customer_notification(self, instance):
        for_date_str = instance.for_date.strftime("%d/%m/%Y")

        msg_short = '{source} - {destination} : {date}'.format(
            source=instance.source.name,
            destination=instance.destination.name,
            date=for_date_str
        )

        msg_long = 'Quote Request accepted for {num_assets} containers of {asset_type} for route {route} dated {date}'.format(
            num_assets=instance.no_of_containers,
            asset_type="{feet}' {identifier}".format(
                identifier=instance.asset.identifier,
                feet=instance.asset.length
            ),
            route=instance.get_route_str(),
            date=for_date_str
        )

        NotificationHelper.send_notification(
            sender_list=[instance.stakeholder, ],
            title='New RFQ Generated',
            message_long=msg_long,
            message_short=msg_short,
            object_id=str (instance.id),
            notification_type=Notification.NOTIFICATION_TYPE_SHIPPER_QUOTE,
            send_email=True

        )



class QuoteSelectedRouteLegsView(generics.RetrieveAPIView):
    serializer_class = serializers.QuoteSelectedRouteLegsSerializer
    permission_classes = [IsAuthenticated, ]

    def get_object(self):
        queryset = self.get_queryset()

        try:
            return queryset.get(
                pk=self.kwargs['pk']
            )
        except queryset.model.DoesNotExist:

            try:
                return queryset.get(
                    quote_number=self.kwargs['pk']
                )
            except queryset.model.DoesNotExist:
                raise Http404

    def get_queryset(self):
        return Quote.objects.filter(stakeholder=self.request.user.stakeholder)


class QuoteLegListCreateView(generics.ListCreateAPIView):
    serializer_class = serializers.LegWithNoOfContainersSerializer
    permission_classes = [IsAuthenticated, ]

    def get_queryset(self):
        stakeholder = self.request.user.stakeholder
        legs = Leg.objects.filter(
            mode__dynamic_table__table_name=settings.VENDOR_MODES[stakeholder.dynamic_table.table_name]
        ).filter(
            quote__stakeholder=stakeholder
        )

        return legs


class QuoteRatesListView(generics.RetrieveAPIView):
    serializer_class = serializers.QuoteRatesSerializer

    # permission_classes = [IsAuthenticated, ]
    def get_object(self):
        queryset = self.get_queryset()

        try:
            return queryset.get(
                quote_number=self.kwargs['pk']
            )
        except queryset.model.DoesNotExist:

            try:
                return queryset.get(
                    pk=self.kwargs['pk']
                )
            except queryset.model.DoesNotExist:
                raise Http404

    def get_queryset(self):
        return Quote.objects.all()


class VendorQuoteRequirementListView(generics.ListAPIView):
    """Return Quote list for bid"""
    serializer_class = serializers.VendorQuoteRequirementListSerializer
    permission_classes = [VendorOnlyAccessPermission, ]
    pagination_class = Camelport15Pagination

    filter_backends = (filters.SearchFilter , filters.OrderingFilter)
    search_fields = ('weight' ,)
    ordering_fields = ('quote_number', 'weight')

    def get_queryset(self):
        # @TODO: filter by country for trucker
        v = Quote.objects.filter(
            for_date__gt=timezone.now(),
            selected_route_num__isnull=False,
            quote_legs__mode__dynamic_table__table_name=settings.VENDOR_MODES[
                self.request.user.stakeholder.dynamic_table.table_name],
            cpbooking__isnull=True
        ).distinct() #.order_by('for_date')

        return v

class VendorDashboard(APIView):
    permission_classes = [VendorOnlyAccessPermission, ]

    def get(self, request, *args, **kwargs):
        response_dict = {
            'winning_bids': [],
            'losing_bids': [],
        }

        return Response(response_dict)


## creating new quote-QuoteRetrieveUpdateDestroyAPIView
class QuoteRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    pagination_class = None
    metadata_class = QuoteMeta
    permission_classes = [IsAuthenticated, ]

    serializer_class = serializers.QuoteSerializer

    def get_queryset(self):
        return Quote.objects.all()