from django.db import models

class CredencialMoodle(models.Model):
    usuario = models.CharField(max_length=50, unique=True, help_text="DNI o Usuario de Moodle")
    contrasena = models.CharField(max_length=255, help_text="Contraseña de Moodle")
    esta_activa = models.BooleanField(default=True, help_text="Indica si el bot debe usar esta cuenta")
    ultima_conexion = models.DateTimeField(null=True, blank=True, help_text="Última vez que el bot entró con éxito")

    def __str__(self):
        return f"Cuenta Moodle: {self.usuario}"

    class Meta:
        verbose_name = "Credencial de Moodle"
        verbose_name_plural = "Credenciales de Moodle"


class TareaAutomatizacion(models.Model):
    curso_nombre = models.CharField(max_length=255, help_text="Nombre exacto del curso. Ej: DISEÑO WEB")
    titulo_general = models.CharField(max_length=255, default="Cronograma general de clases", help_text="Texto a poner en la sección General")
    mensaje_avisos = models.CharField(max_length=255, default="¡Bienvenidos! Es vital cumplir con las tareas.", help_text="Texto motivador para Avisos")
    esta_activa = models.BooleanField(default=True, help_text="Indica si el bot debe procesar este curso")
    ultima_ejecucion = models.DateTimeField(null=True, blank=True, help_text="Última vez que se automatizó")

    def __str__(self):
        return f"Automatizar: {self.curso_nombre}"

    class Meta:
        verbose_name = "Tarea de Automatización"
        verbose_name_plural = "Tareas de Automatización"

class RecursoSemana(models.Model):
    tarea = models.ForeignKey(TareaAutomatizacion, on_delete=models.CASCADE, related_name="recursos_semanas")
    semana_numero = models.PositiveIntegerField(help_text="Número de la semana (1, 2, 3...)")
    titulo = models.CharField(max_length=255, help_text="Título del Área de texto")
    texto = models.TextField(help_text="Contenido detallado para esta semana")
    archivos_carpetas = models.JSONField(
        blank=True, null=True,
        help_text=(
            'Rutas de archivos por carpeta en formato JSON. Soporta listas para varios archivos. Ejemplo: '
            '{"desarrollo": ["C:\\\\ruta\\\\archivo1.pdf", "C:\\\\ruta\\\\archivo2.pdf"], '
            '"analisis": "C:\\\\ruta\\\\otro.pdf"}'
        )
    )

    class Meta:
        verbose_name = "Recurso de Semana"
        verbose_name_plural = "Recursos por Semana"
        ordering = ['semana_numero']

    def __str__(self):
        return f"Semana {self.semana_numero} - {self.titulo}"
