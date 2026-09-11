from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('ai_engine', '0001_initial'),
        ('cases', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='aimodel',
            name='precision',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='aimodel',
            name='recall',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='aimodel',
            name='f1_score',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='aimodel',
            name='created_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='accounts.user',
            ),
        ),
        migrations.AddField(
            model_name='aimodel',
            name='trained_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='aimodel',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='aianalysis',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='doctordecision',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
    ]
