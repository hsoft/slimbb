# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangobb_forum', '0008_auto_20160521_2006'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='markup',
        ),
        migrations.AlterField(
            model_name='post',
            name='markup',
            field=models.CharField(verbose_name='Markup', default='markdown', max_length=15),
        ),
    ]
