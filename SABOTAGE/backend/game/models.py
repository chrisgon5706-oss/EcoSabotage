from django.db import models


class Empresa(models.Model):
    nombre = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    kwh_base_estimado = models.FloatField(default=0)

    def __str__(self):
        return self.nombre


class Usuario(models.Model):
    TRABAJADOR = "TRABAJADOR"
    AUDITOR = "AUDITOR"
    ROLES = [(TRABAJADOR, "Trabajador"), (AUDITOR, "Auditor")]

    username = models.CharField(max_length=50, unique=True)
    rol = models.CharField(max_length=10, choices=ROLES, null=True, blank=True)  # None hasta llenar el lobby
    hamons_saldo = models.IntegerField(default=200)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="usuarios")
    unido = models.BooleanField(default=False)  # ya entró al lobby

    def __str__(self):
        return f"{self.username} ({self.rol or 'sin rol'})"


class TareaEnergia(models.Model):
    titulo = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    min_hamons = models.PositiveIntegerField()
    max_hamons = models.PositiveIntegerField()
    kwh_ahorro_estimado = models.FloatField()

    def __str__(self):
        return self.titulo


class TareaRealizada(models.Model):
    PENDIENTE = "PENDIENTE_AUDITORIA"
    VERIFICADA = "VERIFICADA"
    SABOTEADA = "SABOTEADA"
    ESTADOS = [(PENDIENTE, "Pendiente de auditoría"), (VERIFICADA, "Verificada"), (SABOTEADA, "Saboteada")]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="tareas_realizadas")
    tarea = models.ForeignKey(TareaEnergia, on_delete=models.CASCADE, related_name="realizaciones")
    hamons_ganados = models.IntegerField()
    foto_prueba_url = models.CharField(max_length=500, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=PENDIENTE)
    reportada = models.BooleanField(default=False)  # un solo reporte por tarea

    class Meta:
        ordering = ["-fecha_creacion"]


class PremioSubasta(models.Model):
    titulo = models.CharField(max_length=120)
    costo_base_hamons = models.PositiveIntegerField()
    puja_mas_alta = models.PositiveIntegerField(default=0)
    ganador = models.ForeignKey(
        Usuario, null=True, blank=True, on_delete=models.SET_NULL, related_name="premios_ganados"
    )

    def __str__(self):
        return self.titulo
