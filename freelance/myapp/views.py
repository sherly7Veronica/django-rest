# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import generics



class AssetsListCreateAPIView(generics.ListCreateAPIView):
    queryset = Assets.objects.all()
    serializer_class = UserSerializer


class AssestsListAPIView(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
