"""Private voice-reference metadata (audio itself is not public media)."""

from django.conf import settings
from django.db import models


class VoiceProfile(models.Model):
    """Voice ownership/consent accompanies every stored reference sample."""

    RIGHTS = [
        ("self", "I own this voice"),
        ("licensed", "I have explicit permission"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="readify_voice_profiles",
    )
    name = models.CharField(max_length=80)
    prompt_text = models.CharField(max_length=600)
    rights = models.CharField(max_length=12, choices=RIGHTS)
    consent_confirmed_at = models.DateTimeField()
    sample_key = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_active"], name="v2_voice_user_active_idx")]

    def __str__(self):
        return self.name
