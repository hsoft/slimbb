# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangobb_forum', '0005_remove_profile_theme'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forum',
            name='forum_logo',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='avatar',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='show_avatar',
        ),
    ]
