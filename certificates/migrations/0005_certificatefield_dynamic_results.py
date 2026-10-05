from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('certificates', '0004_certificatefield_font_color_and_more'), ('academics', '0005_academicscheme_academicschemerule'), ('schools', '0001_initial')]

    operations = [
        migrations.AddField(model_name='certificatefield', name='result_value', field=models.CharField(blank=True, choices=[('score', 'Total grade'), ('percentage', 'Percentage')], max_length=20)),
        migrations.AddField(model_name='certificatefield', name='subject', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='certificate_fields', to='academics.subject')),
        migrations.AddField(model_name='certificatefield', name='term', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='certificate_fields', to='schools.term')),
    ]
