# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-08-07 08:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ct', '0025_response_is_preview'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='trial',
            field=models.BooleanField(default=False),
        ),
    ]