hubs.views
-----------------------

.. automodule:: hubs.views
    :members:
    :undoc-members:
    :show-inheritance:


# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cities_light.models import Country
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
# Create your views here.
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from cp_eav.generic_model_serializer import serializer_factory
from hubs.models import Hubs
from hubs.serializer import HubsSerializer, HubsAutoCompleteSerializer, CitiesLightCountrySerializer
from utils.metadata import CPMeta
from utils.pagination import CamelportPagination


class HubsListCreateAPIView(generics.ListCreateAPIView):
    pagination_class = CamelportPagination
    metadata_class = CPMeta
    filter_backends = (DjangoFilterBackend,)

    def get_queryset(self):
        return Hubs.objects.all()

    serializer_class = HubsSerializer


class HubsRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = HubsSerializer

    def get_queryset(self):
        return Hubs.objects.all()


class HubsDynamicValueRUDView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        qs = Hubs.objects.all()
        return qs

    def get_serializer(self, *args, **kwargs):
        dynamic_table = self.get_object().dynamic_table

        ser = serializer_factory(
            mdl=Hubs,
            fields=Hubs.get_fields_list(),
            dyn_table=dynamic_table,
        )
        return ser(*args, **kwargs)


class HubsAutoCompleteListView(generics.ListAPIView):
    pagination_class = CamelportPagination
    metadata_class = CPMeta
    serializer_class = HubsAutoCompleteSerializer
    permission_classes = [IsAuthenticated, ]

    def get_queryset(self):

        search_text = self.request.query_params.get('search')

        if search_text == '%':
            return Hubs.objects.filter(stakeholder=self.request.user.stakeholder)

        query = self.get_query(search_text.split(" "), 'AND', self.request.user.stakeholder.id)

        query_set = Hubs.objects.raw(query)

        result = list(query_set)

        if len(result) == 0:
            query = self.get_query(search_text.split(" "), 'OR', self.request.user.stakeholder.id)

            query_set = Hubs.objects.raw(query)

            result = list(query_set)

        return result

    def get_query(self, texts, appender, stakeholder_id):

        lexeme_search = """to_tsquery('simple', (
                      SELECT string_agg(word, '|')
                      FROM hub_unique_lexeme
                      WHERE similarity(word, '{text}')> 0.25)
                    )"""

        search_condition_boiler_plate = """{amp} document @@ {lexeme_search}"""

        order_by_boilder_plate = """{comma} ts_rank(document, to_tsquery('simple', (
                      SELECT string_agg(word, '|')
                      FROM hub_unique_lexeme
                      WHERE similarity(word, '{text}')> 0.25))
                      )"""

        order_by = search_condition = ''

        for index, text in enumerate(texts):
            if index == 0:
                amp = ''
                comma = ''
            else:
                amp = appender
                comma = ', '

            text = text.replace("'", "''")

            search_condition = search_condition + search_condition_boiler_plate.format(
                lexeme_search=lexeme_search.format(text=text),
                amp=amp
            )

            order_by = order_by + order_by_boilder_plate.format(text=text, comma=comma)

        return """SELECT
                      id, name
                    FROM hub_search_index
                    WHERE (stakeholder_id IS NULL OR stakeholder_id='{stakeholder_id}') AND {condition}
                    ORDER BY {order_by}
                    DESC LIMIT 10;""".format(condition=search_condition, order_by=order_by,
                                             stakeholder_id=stakeholder_id)


class StakeholderHubListView(generics.ListAPIView):
    pagination_class = None
    serializer_class = HubsSerializer

    def get_queryset(self):
        return Hubs.objects.filter(stakeholder__user=self.request.user)


class CountryListView(generics.ListAPIView):
    pagination_class = None
    serializer_class = CitiesLightCountrySerializer

    def get_queryset(self):
        return Country.objects.all().order_by('name')


class ActiveHubListView(generics.ListAPIView):
    pagination_class = None
    serializer_class = HubsSerializer
    permission_classes = [IsAuthenticated, ]

    def get_queryset(self):
        return Hubs.objects.filter(
            Q(
                from_hub_leg__quote__cpbooking__isnull=False,
                from_hub_leg__quote__cpbooking__is_completed=False,
                from_hub_leg__quote__cpbooking__is_active=True,
                from_hub_leg__quote__cpbooking__is_cancelled=False,
                from_hub_leg__quote__stakeholder=self.request.user.stakeholder

            ) |
            Q(
                to_hub_leg__quote__cpbooking__isnull=False,
                to_hub_leg__quote__cpbooking__is_completed=False,
                to_hub_leg__quote__cpbooking__is_active=True,
                to_hub_leg__quote__cpbooking__is_cancelled=False,
                to_hub_leg__quote__stakeholder=self.request.user.stakeholder
            )
        ).distinct()
