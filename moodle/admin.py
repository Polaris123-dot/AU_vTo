from django.contrib import admin
from .models import CredencialMoodle, TareaAutomatizacion, RecursoSemana

@admin.register(CredencialMoodle)
class CredencialMoodleAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'esta_activa', 'ultima_conexion')
    list_filter = ('esta_activa',)
    search_fields = ('usuario',)

class RecursoSemanaInline(admin.TabularInline):
    model = RecursoSemana
    extra = 1

@admin.register(TareaAutomatizacion)
class TareaAutomatizacionAdmin(admin.ModelAdmin):
    list_display = ('curso_nombre', 'titulo_general', 'mensaje_avisos', 'esta_activa', 'ultima_ejecucion')
    list_filter = ('esta_activa',)
    search_fields = ('curso_nombre',)
    inlines = [RecursoSemanaInline]
