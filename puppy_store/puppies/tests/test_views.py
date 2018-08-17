import json
from rest_framework import status
from django.test import TestCase, Client
from django.urls import reverse
from puppies.models import Puppy
from puppies.serializers import PuppySerializer


# initialize the APIClient app
client = Client()
