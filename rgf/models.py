from django.db import models


class ImportRecord(models.Model):
    filename                     = models.CharField(max_length=512)
    gu_id                        = models.CharField(max_length=128, blank=True)
    gu_name                      = models.CharField(max_length=512, blank=True)
    record_id                    = models.BigIntegerField(null=True, blank=True)
    status                       = models.CharField(max_length=32)   # success / skipped / error
    skip_reason                  = models.TextField(blank=True)
    error                        = models.TextField(blank=True)
    url                          = models.URLField(blank=True)
    was_edited                   = models.BooleanField(default=False)  # True = came from import-parsed

    # Full document data as stored/sent to planning.gov.kz
    general_provisions           = models.TextField(blank=True)
    tasks                        = models.JSONField(default=list)
    authorities_rights           = models.JSONField(default=list)
    authorities_responsibilities = models.JSONField(default=list)
    functions                    = models.JSONField(default=list)
    additions                    = models.TextField(blank=True)

    # Denormalised counts for quick display
    tasks_count                  = models.IntegerField(default=0)
    rights_count                 = models.IntegerField(default=0)
    responsibilities_count       = models.IntegerField(default=0)
    functions_count              = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} [{self.status}] @ {self.created_at:%Y-%m-%d %H:%M}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('login',   'Login'),
        ('preview', 'Preview'),
        ('import',  'Import'),
        ('delete',  'Delete'),
    ]

    action     = models.CharField(max_length=32, choices=ACTION_CHOICES)
    filename   = models.CharField(max_length=512, blank=True)
    gu_id      = models.CharField(max_length=128, blank=True)
    gu_name    = models.CharField(max_length=512, blank=True)
    status     = models.CharField(max_length=32, blank=True)   # success / error / skipped
    details    = models.JSONField(default=dict)                 # arbitrary extra context
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} {self.filename or ''} [{self.status}] @ {self.created_at:%Y-%m-%d %H:%M}"
