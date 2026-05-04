from django.core.management.base import BaseCommand
from moodle.services import correr_bot_moodle

class Command(BaseCommand):
    help = 'Ejecuta el bot leyendo las tareas desde el panel de Django Admin'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando el bot usando la configuración de la BD...'))
        correr_bot_moodle()
        self.stdout.write(self.style.SUCCESS('Comando finalizado.'))
