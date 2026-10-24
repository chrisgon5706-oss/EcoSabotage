from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from .models import PremioSubasta, TareaEnergia, TareaRealizada, Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    empresa = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Usuario
        fields = ["id", "username", "rol", "hamons_saldo", "empresa", "unido"]


class TareaEnergiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TareaEnergia
        fields = ["id", "titulo", "descripcion", "min_hamons", "max_hamons", "kwh_ahorro_estimado"]


class TareaRealizadaSerializer(serializers.ModelSerializer):
    trabajador = serializers.CharField(source="usuario.username", read_only=True)
    tarea_titulo = serializers.CharField(source="tarea.titulo", read_only=True)
    segundos_restantes = serializers.SerializerMethodField()

    class Meta:
        model = TareaRealizada
        fields = [
            "id", "trabajador", "tarea_titulo", "hamons_ganados", "foto_prueba_url",
            "fecha_creacion", "estado", "reportada", "segundos_restantes",
        ]

    def get_segundos_restantes(self, obj):
        limite = settings.VENTANA_AUDITORIA_MIN * 60
        transcurrido = (timezone.now() - obj.fecha_creacion).total_seconds()
        return max(0, int(limite - transcurrido))


class PremioSerializer(serializers.ModelSerializer):
    ganador = serializers.CharField(source="ganador.username", read_only=True, default=None)
    siguiente_puja = serializers.SerializerMethodField()

    class Meta:
        model = PremioSubasta
        fields = ["id", "titulo", "costo_base_hamons", "puja_mas_alta", "ganador", "siguiente_puja"]

    def get_siguiente_puja(self, obj):
        if obj.puja_mas_alta:
            return obj.puja_mas_alta + settings.INCREMENTO_PUJA
        return obj.costo_base_hamons
