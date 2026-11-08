from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitoring", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="monitoringsession",
            name="detection_mode",
            field=models.CharField(
                choices=[
                    ("dnn", "Red neuronal YOLO (recomendado)"),
                    ("hog", "Personas (HOG)"),
                    ("motion", "Movimiento (MOG2)"),
                    ("hybrid", "Híbrido (HOG + movimiento)"),
                ],
                default="dnn",
                max_length=20,
                verbose_name="método de detección",
            ),
        ),
    ]
