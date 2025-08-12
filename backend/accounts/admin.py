# accounts/admin.py
from django.contrib import admin
from .models import UserConsent

@admin.register(UserConsent)
class UserConsentAdmin(admin.ModelAdmin):
    list_display = ("user", "privacy_version", "marketing_opt_in", "accepted_terms_at", "client_ip")
    search_fields = ("user__username", "client_ip", "privacy_version")
    list_filter = ("privacy_version", "marketing_opt_in")
