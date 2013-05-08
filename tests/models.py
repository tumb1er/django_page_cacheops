# coding: utf-8

# $Id: $
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=32)


class Module(models.Model):
    name = models.CharField(max_length=32)
    project = models.ForeignKey(Project)

