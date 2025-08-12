# accounts/models.py
from django.db import models
from django.contrib.auth.models import User

class UserConsent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="consent")
    accepted_terms_at = models.DateTimeField(auto_now_add=True)
    privacy_version = models.CharField(max_length=20)
    marketing_opt_in = models.BooleanField(default=False)
    client_ip = models.GenericIPAddressField(null=True, blank=True, unpack_ipv4=True)

    def __str__(self):
        return f"Consent(user={self.user.username}, v={self.privacy_version}, at={self.accepted_terms_at:%Y-%m-%d %H:%M})"
