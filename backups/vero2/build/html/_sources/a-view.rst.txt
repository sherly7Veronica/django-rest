assets.views
-----------------------

.. automodule:: assets.views
    :members:
    :undoc-members:
    :show-inheritance:

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Create your views here.
import json

import requests
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from assets.models import Assets, LDBTracking, FreightCarrier
from assets.serializer import AssetsSerializer, AssetsListSerializer, LDBTrackingSerializer, FreightCarrierSerializers
from cp_eav.generic_model_serializer import serializer_factory
from utils.metadata import CPMeta


class AssetsListCreateAPIView(generics.ListCreateAPIView):
    # pagination_class = CamelportPagination
    metadata_class = CPMeta

    def get_queryset(self):
        return Assets.objects.all()

    serializer_class = AssetsSerializer


class AssetsRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AssetsSerializer

    def get_queryset(self):
        return Assets.objects.all()


class AssetsDynamicValueRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    def get_queryset(self):
        qs = Assets.objects.all()
        return qs

    def get_serializer(self, *args, **kwargs):
        dynamic_table = self.get_object().dynamic_table

        ser = serializer_factory(
            mdl=Assets,
            fields=Assets.get_fields_list(),
            dyn_table=dynamic_table,
        )
        return ser(*args, **kwargs)


class AssetsListAPIView(generics.ListAPIView):
    serializer_class = AssetsListSerializer
    pagination_class = None

    def get_queryset(self):
        return Assets.objects.all()


class LDBTrackingRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = LDBTrackingSerializer

    def get_object(self):
        return get_object_or_404(LDBTracking, container_no=self.kwargs['container_no'])


class MarineTrackingView (APIView):
    def post(self, request, *args, **kwargs):
        response=requests.post (
            url='https://camelport-private-limited.cloud.tyk.io/track/',
            data=request.data
        )

        if 199 < response.status_code < 300:
            return Response (json.loads (response.text))
        # return json.loads (response.text), response.status_code
        # response_text=json.loads (response.text)

        return Response ({'text': response.text.replace (r"\'", "")}, status=response.status_code)

class FreightCarrierAPIView(generics.ListAPIView):
    serializer_class = FreightCarrierSerializers
    pagination_class = None
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FreightCarrier.objects.all()