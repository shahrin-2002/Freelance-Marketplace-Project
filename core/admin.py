from django.contrib import admin

# Register your models here.

from .models import Project

admin.site.register(Project)

from .models import SkillTag

admin.site.register(SkillTag)
