from django.contrib import admin

from .models import Socio, Pago

admin.site.site_header = "La Lonja Admin"
admin.site.site_title = "La Lonja Admin Portal"
admin.site.index_title = "Panel de control del club"


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ('apellido', 'nombre', 'dni', 'telefono', 'email', 'fecha_alta', 'activo')
    search_fields = ('nombre', 'apellido', 'dni', 'telefono')
    list_filter = ('activo', 'fecha_alta')
    ordering = ('apellido', 'nombre')


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('socio', 'mes', 'anio', 'monto', 'fecha_pago')
    search_fields = ('socio__nombre', 'socio__apellido', 'socio__dni')
    list_filter = ('anio', 'mes', 'fecha_pago')
    ordering = ('-anio', '-mes')
