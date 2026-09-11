from django.contrib import admin
from .models import AIModel, AIAnalysis, DoctorDecision
admin.site.register(AIModel)
admin.site.register(AIAnalysis)
admin.site.register(DoctorDecision)
