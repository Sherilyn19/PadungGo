"""Shared usage counter for paid-quota external providers."""
from django.db import models


class ProviderUsage(models.Model):
    """Requests sent to an external provider on one UTC day.

    Stored in the database (not process memory) so both web workers and any
    restart share one count, keeping the app inside the provider's daily quota.
    """

    provider = models.CharField(max_length=40)
    day = models.DateField()
    requests = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["provider", "day"], name="providerusage_unique_provider_day"),
        ]

    def __str__(self) -> str:
        return f"{self.provider} {self.day}: {self.requests}"
