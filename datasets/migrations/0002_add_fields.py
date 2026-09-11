from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('datasets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='dataset',
            name='dataset_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('TABULAR', 'Tabular'),
                    ('IMAGE', 'Image'),
                    ('TEXT', 'Text'),
                    ('MULTIMODAL', 'Multimodal'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='dataset',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='datasets/'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='record_count',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dataset',
            name='uploaded_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='accounts.user',
            ),
        ),
        migrations.AddField(
            model_name='dataset',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dataset',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='dataset',
            name='status',
            field=models.CharField(
                choices=[
                    ('ACTIVE', 'Active'),
                    ('INACTIVE', 'Inactive'),
                    ('PROCESSING', 'Processing'),
                ],
                default='INACTIVE',
                max_length=15,
            ),
        ),
    ]
