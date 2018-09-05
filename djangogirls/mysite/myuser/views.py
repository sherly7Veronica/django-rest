# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from requests.models import Response

from rest_framework import mixins
from rest_framework import generics
from django.shortcuts import get_object_or_404
from models import User
from serializers import UserSerializer


class UserCreateView(generics.CreateAPIView):
    serializer = UserSerializer()

    def create_user(self, request):
        serializer = UserSerializer(request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created"})

        else:
            data = {
                "error": True,
                "errors": serializer.errors
            }
            return Response(data)


class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer()

    def user_details(self, request, pk):
        user = User.objects.get(id=pk)
        serializer = UserSerializer(user)
        return Response(serializer.data)


class UserUpdateView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer()

    def user_update(self, request, pk):
        user = User.objects.get(id=pk)

        if request.method == 'PUT':
            serializer = UserSerializer(user, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)

            else:
                return Response({"errors": serializer.errors,
                                 "error": True})
        serializer = UserSerializer(user)
        return Response(serializer.data)


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer()

    def users_list(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class UserDeleteView(mixins.RetrieveModelMixin, mixins.DestroyModelMixin):
    queryset = User.objects.all()

    def get(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


    def delete_user(self, request, pk):
        user = get_object_or_404(User, id=pk)
        user.delete()
        return Response({"messgae": "deleted"})





