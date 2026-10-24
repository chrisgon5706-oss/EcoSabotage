"""Uso: python manage.py seed_data   (idempotente: limpia y vuelve a cargar)"""
from django.core.management.base import BaseCommand

from game.models import Empresa, PremioSubasta, TareaEnergia, TareaRealizada, Usuario

USUARIOS = ["ana", "bruno", "carla", "diego", "elena", "felipe"]

TAREAS = [
    ("Aire a 24°C", "Deja el aire acondicionado entre 24 y 26 °C.", 80, 180, 1.8),
    ("Apagar luces al salir", "Apaga las luces de salas vacías.", 30, 80, 0.6),
    ("Desconectar equipos", "Desenchufa cargadores y equipos en standby.", 40, 100, 0.9),
    ("Pantalla en modo ahorro", "Activa el ahorro de energía del monitor y suspensión automática.", 20, 60, 0.4),
    ("Usar luz natural", "Abre persianas y apaga lámparas en horas de sol.", 50, 120, 1.1),
]

PREMIOS = [("Medio día libre", 400), ("Bono de almuerzo", 150), ("Parqueo reservado", 250)]


class Command(BaseCommand):
    help = "Carga datos de prueba: 1 empresa, 6 usuarios, 5 tareas y 3 premios."

    def handle(self, *args, **options):
        TareaRealizada.objects.all().delete()
        PremioSubasta.objects.all().delete()
        TareaEnergia.objects.all().delete()
        Usuario.objects.all().delete()
        Empresa.objects.all().delete()

        empresa = Empresa.objects.create(nombre="OptimaTech", sector="Tecnología", kwh_base_estimado=1200)
        for u in USUARIOS:
            Usuario.objects.create(username=u, empresa=empresa, hamons_saldo=200)
        for t, d, mn, mx, kwh in TAREAS:
            TareaEnergia.objects.create(titulo=t, descripcion=d, min_hamons=mn, max_hamons=mx, kwh_ahorro_estimado=kwh)
        for t, c in PREMIOS:
            PremioSubasta.objects.create(titulo=t, costo_base_hamons=c)
        self.stdout.write(self.style.SUCCESS(
            f"Listo: {empresa.nombre}, {len(USUARIOS)} usuarios, {len(TAREAS)} tareas, {len(PREMIOS)} premios."))
