# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.


class Assets(DataBaseModel):
    name = models.CharField(max_length=32)


