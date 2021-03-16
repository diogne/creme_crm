# -*- coding: utf-8 -*-

from django.db import migrations, models
from django.db.models.deletion import CASCADE


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MenuConfigItem',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID',
                    )
                ),
                ('entry_id', models.CharField(editable=False, max_length=100)),
                ('order', models.PositiveIntegerField(editable=False)),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                (
                    'parent',
                    models.ForeignKey(
                        editable=False, null=True, on_delete=CASCADE,
                        related_name='children', to='creme_core.menuconfigitem',
                    )
                ),
            ],
            options={
                'ordering': ('order',),
            },
        ),
    ]
