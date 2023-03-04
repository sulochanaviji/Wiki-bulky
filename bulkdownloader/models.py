from django.db import models

# Create your models here.
class history(models.Model):
    
    command = models.CharField(max_length=250, null=True)
    file_name =  models.CharField(max_length=250, null=True)
    type = models.CharField(max_length=250, null=True)
    tool_type = models.CharField(max_length=250, null=True)
    created_on = models.DateTimeField(null=True)
    created_by = models.CharField(max_length=500, null=True)
    
    class Meta:
        db_table="history"
