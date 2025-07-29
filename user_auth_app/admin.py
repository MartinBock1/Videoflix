from django.contrib import admin
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

# Register your models here.
class OutstandingTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'jti', 'created_at', 'expires_at', 'is_blacklisted')
    search_fields = ('user__username', 'jti')
    list_filter = ('user',)

    def is_blacklisted(self, obj):
        return hasattr(obj, 'blacklistedtoken')
    
    is_blacklisted.boolean = True
    is_blacklisted.short_description = 'Blacklisted?'


class BlacklistedTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_jti', 'get_user', 'blacklisted_at')
    search_fields = ('token__user__username', 'token__jti')

    def get_jti(self, obj):
        return obj.token.jti
    get_jti.short_description = 'Token JTI'

    def get_user(self, obj):
        return obj.token.user
    get_user.short_description = 'User'


admin.site.unregister(OutstandingToken)
admin.site.unregister(BlacklistedToken)

admin.site.register(OutstandingToken, OutstandingTokenAdmin)
admin.site.register(BlacklistedToken, BlacklistedTokenAdmin)
