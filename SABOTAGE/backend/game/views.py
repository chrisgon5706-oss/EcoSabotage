import random
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from .models import Empresa, PremioSubasta, TareaEnergia, TareaRealizada, Usuario
from .serializers import (
    PremioSerializer, TareaEnergiaSerializer, TareaRealizadaSerializer, UsuarioSerializer,
)

# (multiplicador, peso). Valor esperado ~0.93 -> la casa siempre gana un poco.
RULETA = [(0, 35), (0.5, 30), (1.5, 22), (3, 10), (5, 3)]


# ---------- helpers ----------
def _dato(request, clave):
    return request.data.get(clave) if request.method == "POST" else request.query_params.get(clave)


def _usuario(request, rol=None):
    username = (_dato(request, "username") or "").strip()
    if not username:
        raise ValidationError({"detail": "Falta el campo 'username'."})
    user = Usuario.objects.filter(username=username).select_related("empresa").first()
    if not user:
        raise NotFound("Usuario no encontrado. Únete primero al lobby.")
    if rol and user.rol != rol:
        raise ValidationError({"detail": f"Esta acción es solo para el rol {rol}."})
    return user


def _empresa():
    empresa = Empresa.objects.first()
    if not empresa:
        raise NotFound("No hay empresa. Ejecuta: python manage.py seed_data")
    return empresa


def _consolidar():
    """Pasados 15 min la tarea queda firme: ya no se puede sabotear."""
    limite = timezone.now() - timedelta(minutes=settings.VENTANA_AUDITORIA_MIN)
    TareaRealizada.objects.filter(
        estado=TareaRealizada.PENDIENTE, fecha_creacion__lt=limite
    ).update(estado=TareaRealizada.VERIFICADA)


def _foto_es_falsa(url):
    """Verificación simulada para el MVP: sin URL o con marcas 'fake'/'falsa' => falsa.
    En producción aquí iría un modelo de visión o revisión humana."""
    u = (url or "").lower()
    return (not u) or "fake" in u or "falsa" in u


def _estado_lobby(empresa):
    miembros = list(Usuario.objects.filter(empresa=empresa).order_by("id"))
    unidos = [m for m in miembros if m.unido]
    return {
        "jugadores": len(unidos),
        "total": settings.LOBBY_SIZE,
        "roles_asignados": any(m.rol for m in unidos),
        "miembros": [{"username": m.username, "unido": m.unido} for m in miembros],
        "empresa": empresa.nombre,
    }


# ---------- lobby ----------
@api_view(["POST"])
def unirse_lobby(request):
    username = (request.data.get("username") or "").strip()
    if not username:
        raise ValidationError({"detail": "Escribe un nombre de usuario."})
    empresa = _empresa()
    with transaction.atomic():
        user = Usuario.objects.filter(username=username).first()
        if user is None:
            if Usuario.objects.filter(empresa=empresa).count() >= settings.LOBBY_SIZE:
                raise ValidationError({"detail": "El lobby ya está lleno."})
            user = Usuario.objects.create(username=username, empresa=empresa)
        user.unido = True
        user.save(update_fields=["unido"])

        unidos = list(Usuario.objects.filter(empresa=empresa, unido=True))
        if len(unidos) >= settings.LOBBY_SIZE and not any(u.rol for u in unidos):
            random.shuffle(unidos)
            for i, u in enumerate(unidos):
                u.rol = Usuario.AUDITOR if i == 0 else Usuario.TRABAJADOR
                u.save(update_fields=["rol"])
        user.refresh_from_db()
    return Response({"usuario": UsuarioSerializer(user).data, "lobby": _estado_lobby(empresa)})


@api_view(["GET"])
def estado_lobby(request):
    return Response(_estado_lobby(_empresa()))


@api_view(["POST"])
def reiniciar_demo(request):
    """Utilidad de demo: vuelve a empezar la partida (roles, saldos, tareas y subasta)."""
    TareaRealizada.objects.all().delete()
    Usuario.objects.update(rol=None, unido=False, hamons_saldo=200)
    PremioSubasta.objects.update(puja_mas_alta=0, ganador=None)
    return Response({"detail": "Partida reiniciada."})


@api_view(["GET"])
def perfil_usuario(request):
    _consolidar()
    return Response(UsuarioSerializer(_usuario(request)).data)


# ---------- tareas ----------
@api_view(["GET"])
def listar_tareas(request):
    return Response(TareaEnergiaSerializer(TareaEnergia.objects.all(), many=True).data)


@api_view(["POST"])
def completar_tarea(request):
    user = _usuario(request, rol=Usuario.TRABAJADOR)
    tarea = TareaEnergia.objects.filter(pk=request.data.get("tarea_id")).first()
    if not tarea:
        raise NotFound("Tarea no encontrada.")
    ganados = random.randint(tarea.min_hamons, tarea.max_hamons)
    with transaction.atomic():
        realizada = TareaRealizada.objects.create(
            usuario=user, tarea=tarea, hamons_ganados=ganados,
            foto_prueba_url=(request.data.get("foto_prueba_url") or "").strip(),
        )
        user.hamons_saldo += ganados
        user.save(update_fields=["hamons_saldo"])
    return Response(
        {"tarea_realizada": TareaRealizadaSerializer(realizada).data,
         "hamons_ganados": ganados, "nuevo_saldo": user.hamons_saldo},
        status=status.HTTP_201_CREATED,
    )


# ---------- auditor ----------
@api_view(["GET"])
def historial_auditor(request):
    _usuario(request, rol=Usuario.AUDITOR)
    _consolidar()
    desde = timezone.now() - timedelta(minutes=settings.VENTANA_AUDITORIA_MIN)
    qs = TareaRealizada.objects.filter(fecha_creacion__gte=desde).select_related("usuario", "tarea")
    return Response(TareaRealizadaSerializer(qs, many=True).data)


@api_view(["POST"])
def reportar_falsedad(request):
    auditor = _usuario(request, rol=Usuario.AUDITOR)
    _consolidar()
    with transaction.atomic():
        t = (TareaRealizada.objects.select_for_update().select_related("usuario")
             .filter(pk=request.data.get("tarea_realizada_id")).first())
        if not t:
            raise NotFound("Tarea realizada no encontrada.")
        if t.reportada:
            raise ValidationError({"detail": "Esta tarea ya fue reportada."})
        if t.estado != TareaRealizada.PENDIENTE:
            raise ValidationError({"detail": "Pasaron más de 15 minutos: la tarea ya quedó firme."})

        t.reportada = True
        if _foto_es_falsa(t.foto_prueba_url):
            trabajador = t.usuario
            robo = min(t.hamons_ganados, trabajador.hamons_saldo)
            trabajador.hamons_saldo -= robo
            auditor.hamons_saldo += robo
            trabajador.save(update_fields=["hamons_saldo"])
            t.estado = TareaRealizada.SABOTEADA
            resultado = {"valida": True, "hamons_robados": robo,
                         "mensaje": f"Denuncia válida: le robaste {robo} Hamons a {trabajador.username}."}
        else:
            auditor.hamons_saldo = max(0, auditor.hamons_saldo - settings.PENALIZACION_AUDITOR)
            t.estado = TareaRealizada.VERIFICADA
            resultado = {"valida": False, "hamons_robados": 0,
                         "mensaje": f"Denuncia rechazada: la foto era válida. Penalización de -{settings.PENALIZACION_AUDITOR} Hamons."}
        auditor.save(update_fields=["hamons_saldo"])
        t.save(update_fields=["reportada", "estado"])
    resultado["nuevo_saldo"] = auditor.hamons_saldo
    return Response(resultado)


# ---------- ruleta ----------
@api_view(["POST"])
def girar_ruleta(request):
    user = _usuario(request)  # Trabajadores y Auditor pueden jugar
    costo = settings.COSTO_RULETA
    if not user.rol:
        raise ValidationError({"detail": "La partida aún no empieza."})
    with transaction.atomic():
        if user.hamons_saldo < costo:
            raise ValidationError({"detail": f"Necesitas {costo} Hamons para girar."})
        mult = random.choices([m for m, _ in RULETA], weights=[w for _, w in RULETA])[0]
        premio = int(costo * mult)
        user.hamons_saldo += premio - costo
        user.save(update_fields=["hamons_saldo"])
    return Response({"multiplicador": mult, "premio": premio, "costo": costo,
                     "jackpot": mult == 5, "nuevo_saldo": user.hamons_saldo})


# ---------- subasta ----------
@api_view(["GET"])
def listar_subasta(request):
    return Response(PremioSerializer(PremioSubasta.objects.all().order_by("id"), many=True).data)


@api_view(["POST"])
def pujar(request):
    user = _usuario(request)
    try:
        monto = int(request.data.get("monto"))
    except (TypeError, ValueError):
        raise ValidationError({"detail": "Monto inválido."})
    with transaction.atomic():
        premio = PremioSubasta.objects.select_for_update().filter(pk=request.data.get("premio_id")).first()
        if not premio:
            raise NotFound("Premio no encontrado.")
        if monto < premio.costo_base_hamons or monto <= premio.puja_mas_alta:
            raise ValidationError({"detail": "Tu puja debe superar la puja más alta y el precio base."})
        if premio.ganador_id == user.id:
            raise ValidationError({"detail": "Ya vas ganando este premio."})
        if user.hamons_saldo < monto:
            raise ValidationError({"detail": "No tienes Hamons suficientes."})
        # Los Hamons de la puja quedan retenidos; al ser superada se devuelven.
        if premio.ganador:
            anterior = premio.ganador
            anterior.hamons_saldo += premio.puja_mas_alta
            anterior.save(update_fields=["hamons_saldo"])
        user.hamons_saldo -= monto
        user.save(update_fields=["hamons_saldo"])
        premio.puja_mas_alta, premio.ganador = monto, user
        premio.save(update_fields=["puja_mas_alta", "ganador"])
    return Response({"premio": PremioSerializer(premio).data, "nuevo_saldo": user.hamons_saldo})


# ---------- impacto ----------
@api_view(["GET"])
def impacto_empresa(request):
    _consolidar()
    empresa = _empresa()
    tareas = TareaRealizada.objects.filter(usuario__empresa=empresa).exclude(
        estado=TareaRealizada.SABOTEADA).select_related("tarea")
    kwh = round(sum(t.tarea.kwh_ahorro_estimado for t in tareas), 2)
    cop = round(kwh * settings.COP_POR_KWH)
    co2 = round(kwh * settings.KG_CO2_POR_KWH, 2)
    arboles = round(co2 / settings.KG_CO2_POR_ARBOL_ANIO, 2)
    pct = round(100 * kwh / empresa.kwh_base_estimado, 2) if empresa.kwh_base_estimado else 0
    return Response({
        "empresa": empresa.nombre, "tareas_validas": tareas.count(),
        "tareas_saboteadas": TareaRealizada.objects.filter(
            usuario__empresa=empresa, estado=TareaRealizada.SABOTEADA).count(),
        "kwh_ahorrados": kwh, "cop_ahorrados": cop, "co2_kg_evitados": co2,
        "arboles_equivalentes": arboles, "porcentaje_sobre_base": pct,
        "ods": ["ODS 7: Energía asequible y no contaminante",
                "ODS 12: Producción y consumo responsables"],
        "supuestos": {"cop_por_kwh": settings.COP_POR_KWH, "kg_co2_por_kwh": settings.KG_CO2_POR_KWH,
                      "kg_co2_por_arbol_anio": settings.KG_CO2_POR_ARBOL_ANIO,
                      "nota": "Valores estimativos de demostración; reemplazar con datos de factura."},
    })
