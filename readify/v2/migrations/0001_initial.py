# Generated for the V2 voice profile metadata. Original legacy app migrations remain separate.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VoiceProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80)),
                ("prompt_text", models.CharField(max_length=600)),
                ("rights", models.CharField(choices=[("self", "I own this voice"), ("licensed", "I have explicit permission")], max_length=12)),
                ("consent_confirmed_at", models.DateTimeField()),
                ("sample_key", models.CharField(max_length=100, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_active", models.BooleanField(default=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="readify_voice_profiles", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="voiceprofile",
            index=models.Index(fields=["user", "is_active"], name="v2_voice_user_active_idx"),
        ),
    ]
