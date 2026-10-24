# EcoSabotage

Juego social para que los empleados de una empresa ahorren energía durante El Niño.
Hackathon **Barranquilla No Se Apaga** (24 de octubre de 2026) · **Línea 2: EcoFriends**.

Seis compañeros de una empresa (ej. OptimaTech) entran a un lobby. El sistema sortea **1 Auditor** (impostor)
y **5 Trabajadores**. Los trabajadores completan tareas de ahorro con foto-prueba y ganan **Hamons**;
el Auditor tiene 15 minutos para detectar fotos falsas y robar los Hamons. Todos pueden apostar en la
**Ruleta Energética** y pujar en la **Subasta** de premios corporativos. Un dashboard final muestra kWh, COP y CO₂
ahorrados, ligados a los **ODS 7 y 12**.

## Autores

- Cristian Gonzalez Beleño
- _(agrega aquí a tus compañeros de equipo)_

## Reglas del juego

| Mecánica | Regla |
|---|---|
| Lobby | 6 jugadores; al entrar el sexto se asignan roles al azar |
| Tareas | Cada tarea da Hamons aleatorios dentro de su rango (ej. Aire a 24°C: 80–180) |
| Ruleta | 50 Hamons por giro: x0, x0.5, x1.5, x3, x5 (jackpot). La pueden jugar Trabajadores y Auditor |
| Auditoría | El Auditor tiene 15 min por tarea. Reporte válido: roba los Hamons. Reporte rechazado: -100 Hamons |
| Subasta | Puja mínima = precio base; luego +50. Los Hamons quedan retenidos y se devuelven si te superan |
| Impacto | Suma de kWh de las tareas **no saboteadas** |

**Verificación anti-fraude (MVP):** el backend considera falsa una foto-prueba sin URL o cuya URL contenga
`fake` o `falsa`. En el frontend, la casilla _"Simular foto falsa (demo)"_ genera ese caso. En producción
se reemplazaría por visión por computador o revisión humana (`_foto_es_falsa` en `game/views.py`).

**Factores de conversión estimativos** (editables en `backend/config/settings.py`): 800 COP/kWh,
0.126 kg CO₂/kWh, 22 kg CO₂ absorbidos por árbol al año. Reemplázalos con datos reales de factura.

## Instalación y ejecución

Requisitos: Python 3.10+, Node.js 18+.

### 1. Backend (Django REST Framework)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data          # 1 empresa, 6 usuarios, 5 tareas, 3 premios
python manage.py runserver          # http://localhost:8000
```

### 2. Frontend (Angular 18)

```bash
npx @angular/cli@18 new frontend-app --standalone --style=css --routing=false --ssr=false --skip-git --defaults
cd frontend-app
# Copia los archivos de ../frontend/src sobre los de src/ (main.ts, index.html, styles.css y la carpeta app/)
cp -r ../frontend/src/* src/
npx ng serve                        # http://localhost:4200
```

### 3. Jugar la demo

1. Abre `http://localhost:4200` en **6 ventanas/perfiles** (o ventanas privadas) y entra con `ana`, `bruno`, `carla`, `diego`, `elena` y `felipe` (botones de demo rápida).
2. Al entrar el sexto, todos ven la animación de rol y pasan al dashboard.
3. Trabajadores: completan tareas. Auditor: reporta desde su panel.
4. ¿Quieres repetir? Botón _Reiniciar partida (demo)_ en el lobby, o `python manage.py seed_data`.

## API

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/lobby/unirse/` | `{username}` — entra al lobby; al llegar a 6 asigna roles |
| GET | `/api/lobby/estado/` | Jugadores X/6 |
| POST | `/api/lobby/reiniciar/` | Reinicia la partida (demo) |
| GET | `/api/usuario/?username=` | Saldo y rol |
| GET | `/api/tareas/` | Tareas disponibles |
| POST | `/api/tareas/completar/` | `{username, tarea_id, foto_prueba_url}` |
| GET | `/api/auditor/historial/?username=` | Tareas de los últimos 15 min (solo Auditor) |
| POST | `/api/auditor/reportar/` | `{username, tarea_realizada_id}` |
| POST | `/api/gambling/ruleta/` | `{username}` — cuesta 50 Hamons |
| GET | `/api/subasta/` | Premios y pujas |
| POST | `/api/subasta/pujar/` | `{username, premio_id, monto}` |
| GET | `/api/impacto-empresa/` | kWh, COP, CO₂, árboles |

## Alcance del MVP

Los datos son de muestra y no se conecta a Air-e ni a la Cámara de Comercio. No hay autenticación real
(el jugador se identifica solo por su `username`) y la subasta se actualiza por _polling_ cada 2.5 s.

## Licencia

MIT — ver [LICENSE](LICENSE).
