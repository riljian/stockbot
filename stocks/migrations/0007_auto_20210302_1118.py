# Generated by Django 3.1.6 on 2021-03-02 11:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0006_fill_category_name'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='dailysummary',
            index=models.Index(fields=['-date'], name='stocks_dail_date_9a76c3_idx'),
        ),
        migrations.AddIndex(
            model_name='dailysummary',
            index=models.Index(fields=['-date', 'stock'], name='stocks_dail_date_078f87_idx'),
        ),
    ]
