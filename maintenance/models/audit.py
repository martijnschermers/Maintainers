import hashlib

from django.conf import settings
from django.db import models

from .vehicles import Vehicle


class AuditLog(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="audit_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100)
    object_id = models.PositiveBigIntegerField()
    payload = models.JSONField(default=dict)
    previous_hash = models.CharField(max_length=64, blank=True)
    record_hash = models.CharField(max_length=64, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.record_hash:
            previous = self.vehicle.audit_logs.order_by("-created_at", "-pk").first()
            self.previous_hash = previous.record_hash if previous else ""
            content = (
                f"{self.vehicle_id}|{self.action}|{self.object_type}|{self.object_id}|"
                f"{self.payload}|{self.previous_hash}"
            )
            self.record_hash = hashlib.sha256(content.encode()).hexdigest()
        super().save(*args, **kwargs)
