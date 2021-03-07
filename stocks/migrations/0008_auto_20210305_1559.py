# Generated by Django 3.1.6 on 2021-03-05 15:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0007_auto_20210302_1118'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tick',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False)),
                ('ts', models.DateTimeField()),
                ('close', models.FloatField()),
                ('volume', models.IntegerField()),
                ('bid_price', models.FloatField()),
                ('bid_volume', models.IntegerField()),
                ('ask_price', models.FloatField()),
                ('ask_volume', models.IntegerField()),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ticks', to='stocks.stock')),
            ],
        ),
        migrations.AddIndex(
            model_name='tick',
            index=models.Index(fields=['-ts'], name='stocks_tick_ts_fa5323_idx'),
        ),
        migrations.AddIndex(
            model_name='tick',
            index=models.Index(fields=['-ts', 'stock'], name='stocks_tick_ts_5cc362_idx'),
        ),
    ]
