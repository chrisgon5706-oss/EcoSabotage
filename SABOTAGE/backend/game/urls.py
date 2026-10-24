from django.urls import path

from . import views

urlpatterns = [
    path("lobby/unirse/", views.unirse_lobby),
    path("lobby/estado/", views.estado_lobby),
    path("lobby/reiniciar/", views.reiniciar_demo),
    path("usuario/", views.perfil_usuario),
    path("tareas/", views.listar_tareas),
    path("tareas/completar/", views.completar_tarea),
    path("auditor/historial/", views.historial_auditor),
    path("auditor/reportar/", views.reportar_falsedad),
    path("gambling/ruleta/", views.girar_ruleta),
    path("subasta/", views.listar_subasta),
    path("subasta/pujar/", views.pujar),
    path("impacto-empresa/", views.impacto_empresa),
]
