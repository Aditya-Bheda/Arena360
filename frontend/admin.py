# # from django.contrib import admin

# # # Register your models here.

# from django.contrib import admin
# from .models import Sport, SportsClub

# @admin.register(Sport)
# class SportAdmin(admin.ModelAdmin):
#     list_display = ('name',)

# @admin.register(SportsClub)
# class SportsClubAdmin(admin.ModelAdmin):
#     list_display = ('club_name', 'owner', 'location', 'price_per_hour', 'approved', 'created_at')
#     list_filter = ('approved', 'sports')
#     search_fields = ('club_name', 'location', 'owner__username', 'contact_number')
#     actions = ['approve_clubs']

#     def approve_clubs(self, request, queryset):
#         updated = queryset.update(approved=True)
#         self.message_user(request, f"{updated} club(s) approved.")
#     approve_clubs.short_description = "Approve selected clubs"

from django.contrib import admin
from .models import SportsClub, Sport
from .models import UserProfile

admin.site.register(UserProfile)

@admin.register(SportsClub)
class SportsClubAdmin(admin.ModelAdmin):
    list_display = ('club_name', 'owner', 'approved')
    list_filter = ('approved',)
    search_fields = ('club_name', 'location', 'owner__username')

    actions = ['approve_clubs', 'reject_clubs']

    def approve_clubs(self, request, queryset):
        queryset.update(approved=True)
        self.message_user(request, "Selected clubs have been approved.")

    def reject_clubs(self, request, queryset):
        queryset.update(approved=False)
        self.message_user(request, "Selected clubs have been marked as pending.")

@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ('name',)
