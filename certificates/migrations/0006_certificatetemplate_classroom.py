from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('certificates', '0005_certificatefield_dynamic_results'), ('academics', '0005_academicscheme_academicschemerule')]
    operations = [migrations.AddField(model_name='certificatetemplate', name='classroom', field=models.ForeignKey(blank=True, help_text='Optional: limits this design to one classroom and its subjects.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='certificate_templates', to='academics.classroom'))]
