# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangobb_forum', '0007_auto_20160521_1527'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='privacy_permission',
        ),
        migrations.AlterField(
            model_name='post',
            name='markup',
            field=models.CharField(verbose_name='Markup', max_length=15, default='bbcode', choices=[('bbcode', 'bbcode'), ('markdown', 'markdown')]),
        ),
        migrations.AlterField(
            model_name='profile',
            name='markup',
            field=models.CharField(verbose_name='Default markup', max_length=15, default='bbcode', choices=[('bbcode', 'bbcode'), ('markdown', 'markdown')]),
        ),
    ]
