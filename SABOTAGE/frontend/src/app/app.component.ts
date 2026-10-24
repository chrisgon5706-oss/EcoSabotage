import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

const API = 'http://localhost:8000/api';

type Vista = 'lobby' | 'juego' | 'ruleta' | 'subasta' | 'impacto';

interface Usuario { username: string; rol: 'TRABAJADOR' | 'AUDITOR' | null; hamons_saldo: number; empresa: string; }
interface Lobby { jugadores: number; total: number; roles_asignados: boolean; empresa: string; miembros: { username: string; unido: boolean }[]; }
interface Tarea { id: number; titulo: string; descripcion: string; min_hamons: number; max_hamons: number; kwh_ahorro_estimado: number; }
interface Realizada {
  id: number; trabajador: string; tarea_titulo: string; hamons_ganados: number; foto_prueba_url: string;
  estado: string; reportada: boolean; segundos_restantes: number; recibidoEn?: number;
}
interface Premio { id: number; titulo: string; costo_base_hamons: number; puja_mas_alta: number; ganador: string | null; siguiente_puja: number; }
interface Impacto {
  empresa: string; kwh_ahorrados: number; cop_ahorrados: number; co2_kg_evitados: number; arboles_equivalentes: number;
  porcentaje_sobre_base: number; tareas_validas: number; tareas_saboteadas: number; ods: string[];
  supuestos: { nota: string };
}

// Orden de los sectores de la rueda (cada uno ocupa 72°)
const SECTORES = [0, 0.5, 1.5, 3, 5];

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnInit, OnDestroy {
  vista: Vista = 'lobby';
  usuarioNombre = '';
  usuario: Usuario | null = null;
  lobby: Lobby | null = null;
  revelandoRol = false;

  tareas: Tarea[] = [];
  historial: Realizada[] = [];
  premios: Premio[] = [];
  impacto: Impacto | null = null;
  simularFotoFalsa = false;

  ahora = Date.now();
  gananciaPopup: number | null = null;
  mensaje = '';
  mensajeTipo: 'ok' | 'error' = 'ok';

  sectores = SECTORES;
  rotacion = 0;
  girando = false;
  resultadoRuleta: { multiplicador: number; premio: number; jackpot: boolean } | null = null;

  private poll?: ReturnType<typeof setInterval>;
  private reloj?: ReturnType<typeof setInterval>;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    const guardado = localStorage.getItem('ecosabotage_user');
    if (guardado) { this.usuarioNombre = guardado; this.unirse(); }
    this.reloj = setInterval(() => (this.ahora = Date.now()), 1000);
    this.poll = setInterval(() => this.refrescar(), 2500);
  }

  ngOnDestroy() { clearInterval(this.poll); clearInterval(this.reloj); }

  // ---------- utilidades ----------
  get esAuditor() { return this.usuario?.rol === 'AUDITOR'; }

  private aviso(texto: string, tipo: 'ok' | 'error' = 'ok') {
    this.mensaje = texto; this.mensajeTipo = tipo;
    setTimeout(() => { if (this.mensaje === texto) this.mensaje = ''; }, 4500);
  }

  private errorMsg(err: any) { return err?.error?.detail || 'No se pudo conectar con el servidor (¿está corriendo Django en :8000?).'; }

  irA(v: Vista) {
    this.vista = v;
    this.refrescar();
  }

  // ---------- lobby ----------
  elegir(nombre: string) { this.usuarioNombre = nombre; this.unirse(); }

  unirse() {
    const nombre = this.usuarioNombre.trim();
    if (!nombre) return;
    this.http.post<{ usuario: Usuario; lobby: Lobby }>(`${API}/lobby/unirse/`, { username: nombre }).subscribe({
      next: (r) => {
        localStorage.setItem('ecosabotage_user', nombre);
        this.usuario = r.usuario; this.lobby = r.lobby;
        this.cargarTareas();
        if (r.lobby.roles_asignados && r.usuario.rol) this.revelarRol();
      },
      error: (e) => { localStorage.removeItem('ecosabotage_user'); this.aviso(this.errorMsg(e), 'error'); },
    });
  }

  private revelarRol() {
    if (this.revelandoRol || this.vista !== 'lobby') return;
    this.revelandoRol = true;
    setTimeout(() => { this.revelandoRol = false; this.irA('juego'); }, 3200);
  }

  salir() {
    localStorage.removeItem('ecosabotage_user');
    this.usuario = null; this.usuarioNombre = ''; this.vista = 'lobby';
  }

  reiniciar() {
    this.http.post(`${API}/lobby/reiniciar/`, {}).subscribe(() => { this.salir(); this.aviso('Partida reiniciada'); });
  }

  // ---------- refresco periódico ----------
  refrescar() {
    if (!this.usuario) return;
    const q = `username=${encodeURIComponent(this.usuario.username)}`;
    this.http.get<Usuario>(`${API}/usuario/?${q}`).subscribe({ next: (u) => (this.usuario = u), error: () => {} });

    if (this.vista === 'lobby') {
      this.http.get<Lobby>(`${API}/lobby/estado/`).subscribe((l) => {
        this.lobby = l;
        if (l.roles_asignados && this.usuario?.rol) this.revelarRol();
      });
    }
    if (this.vista === 'juego' && this.esAuditor) {
      this.http.get<Realizada[]>(`${API}/auditor/historial/?${q}`).subscribe((h) => {
        const t = Date.now();
        this.historial = h.map((x) => ({ ...x, recibidoEn: t }));
      });
    }
    if (this.vista === 'subasta') this.http.get<Premio[]>(`${API}/subasta/`).subscribe((p) => (this.premios = p));
    if (this.vista === 'impacto') this.http.get<Impacto>(`${API}/impacto-empresa/`).subscribe((i) => (this.impacto = i));
  }

  // ---------- juego ----------
  cargarTareas() { this.http.get<Tarea[]>(`${API}/tareas/`).subscribe((t) => (this.tareas = t)); }

  completar(t: Tarea) {
    if (!this.usuario) return;
    const semilla = (this.simularFotoFalsa ? 'fake-' : 'ok-') + Date.now();
    const foto = `https://picsum.photos/seed/${semilla}/400/260`;
    this.http.post<any>(`${API}/tareas/completar/`, { username: this.usuario.username, tarea_id: t.id, foto_prueba_url: foto }).subscribe({
      next: (r) => {
        this.usuario!.hamons_saldo = r.nuevo_saldo;
        this.gananciaPopup = r.hamons_ganados;
        setTimeout(() => (this.gananciaPopup = null), 2200);
      },
      error: (e) => this.aviso(this.errorMsg(e), 'error'),
    });
  }

  restante(t: Realizada): number {
    return Math.max(0, t.segundos_restantes - Math.floor((this.ahora - (t.recibidoEn ?? this.ahora)) / 1000));
  }

  fmt(seg: number): string {
    const m = Math.floor(seg / 60).toString().padStart(2, '0');
    const s = (seg % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  reportar(t: Realizada) {
    if (!this.usuario) return;
    this.http.post<any>(`${API}/auditor/reportar/`, { username: this.usuario.username, tarea_realizada_id: t.id }).subscribe({
      next: (r) => { this.usuario!.hamons_saldo = r.nuevo_saldo; this.aviso(r.mensaje, r.valida ? 'ok' : 'error'); this.refrescar(); },
      error: (e) => this.aviso(this.errorMsg(e), 'error'),
    });
  }

  // ---------- ruleta ----------
  girar() {
    if (!this.usuario || this.girando) return;
    this.http.post<any>(`${API}/gambling/ruleta/`, { username: this.usuario.username }).subscribe({
      next: (r) => {
        this.girando = true; this.resultadoRuleta = null;
        const idx = SECTORES.indexOf(r.multiplicador);
        const base = this.rotacion - (this.rotacion % 360);
        this.rotacion = base + 360 * 6 + (360 - (idx * 72 + 36));
        setTimeout(() => {
          this.girando = false;
          this.resultadoRuleta = r;
          this.usuario!.hamons_saldo = r.nuevo_saldo;
        }, 3600);
      },
      error: (e) => this.aviso(this.errorMsg(e), 'error'),
    });
  }

  // ---------- subasta ----------
  pujar(p: Premio) {
    if (!this.usuario) return;
    this.http.post<any>(`${API}/subasta/pujar/`, { username: this.usuario.username, premio_id: p.id, monto: p.siguiente_puja }).subscribe({
      next: (r) => { this.usuario!.hamons_saldo = r.nuevo_saldo; this.aviso(`Vas ganando: ${p.titulo}`); this.refrescar(); },
      error: (e) => this.aviso(this.errorMsg(e), 'error'),
    });
  }

  nf(n: number) { return n.toLocaleString('es-CO'); }
}
