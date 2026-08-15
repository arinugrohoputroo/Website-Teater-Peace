from django.contrib import admin

from .models import CommitteeMember, SnackClaim, SnackSession


@admin.register(CommitteeMember)
class CommitteeMemberAdmin(admin.ModelAdmin):
    list_display = ['member_code', 'name', 'active', 'qr_token', 'created_at']
    list_filter = ['active']
    search_fields = ['name', 'member_code', 'qr_token']
    readonly_fields = ['qr_token', 'normalized_name', 'created_at', 'updated_at']


@admin.register(SnackSession)
class SnackSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'start_time', 'end_time', 'active']


@admin.register(SnackClaim)
class SnackClaimAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'session', 'claimed_at', 'operator', 'detection_method']
    list_filter = ['session', 'detection_method']
    search_fields = ['committee_member__name', 'committee_member__member_code', 'qr_token_used']
