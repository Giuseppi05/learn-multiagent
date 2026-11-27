# Aprende Multiagente

Sistema multiagente basado en IA para personalizar contenido pedagógico en estudiantes de primaria de Lima (2026).

## Despliegue

| Componente | Plataforma | Enlace |
| --- | --- | --- |
| Demo (frontend Next.js) | Vercel | https://learn-multiagent.vercel.app |
| API (FastAPI, Orquestador y agentes) | Render | https://learn-multiagent.onrender.com/health |
| Base de datos y autenticación | Supabase | — |
| Maqueta de Isla Aprende (XR) | GitHub Pages | https://giuseppi05.github.io/learn-island/ |

## Problema

El docente de primaria prepara, adapta y corrige a mano el material de cada estudiante. Con aulas numerosas termina usando un material de «talla única» que no responde a los distintos niveles y ritmos. Este sistema automatiza el diagnóstico, la generación, la adaptación y la evaluación con agentes de IA. El docente pasa a supervisar y validar: nada llega al estudiante sin su aprobación.

## Arquitectura

```
Next.js (docente · estudiante · coordinación)
        │  token de Supabase Auth
        ▼
FastAPI ── reglas de la Sección 16 (clasificación y semáforo)
        │
        ▼
Orquestador (LangGraph) ── único que lee y escribe en la base
   ├─ Agente de Diagnóstico        (CU-IA-01)
   ├─ Agente Generador             (CU-IA-02 y prueba inicial)
   ├─ Agente de Adaptación         (CU-IA-03)
   ├─ Agente Evaluador             (CU-IA-04 y CU-IA-06)
   ├─ Asistente de dudas           (CU-IA-05)
   └─ Agente de Refuerzo Conceptual (Sección 21)
        │                                   │
        ▼                                   ▼
   Gemini API (salida JSON validada)   Supabase (PostgreSQL + Auth)
```

- **Dos grafos de LangGraph.** El primero genera el contenido: genera y adapta, o arma la prueba inicial. El segundo procesa las respuestas: evalúa, diagnostica o refuerza, decide con las últimas 3 a 5 respuestas y prepara el siguiente material.
- **Supervisión humana.** El docente aprueba, devuelve con observaciones (el material se regenera con ellas) o rechaza. Tras 3 devoluciones, el ciclo automático se detiene.
- **Fallas de la IA.** Cada salida se valida con Pydantic. Si no es válida, se reintenta hasta 3 veces con espera exponencial, y luego el caso queda marcado para el docente. No hay respuestas inventadas.
- **Trazabilidad.** Cada llamada a un agente guarda su entrada, su salida, el modelo usado, los intentos y la latencia.
- **Protección de datos.** Al modelo solo le llega un código interno (por ejemplo, `E263B-01`), nunca el nombre. Las tablas tienen RLS activo y la API pública de datos de Supabase está desactivada.
- **Roles.** La coordinación crea a los docentes y las aulas. El docente gestiona a sus estudiantes, que entran con un usuario y un PIN de 6 dígitos.
- **Mando físico.** `POST /devices/events` está protegido con una clave de dispositivo y no duplica mensajes.

## Tecnologías

Next.js 15 (React y TypeScript), Tailwind, Recharts · FastAPI, SQLAlchemy, Alembic · LangGraph · Gemini API (`google-genai`) · Supabase (PostgreSQL y Auth) · Pytest, Ruff, ESLint · GitHub Actions.

## Cómo ejecutarlo

Requisitos: Python 3.12 o superior, Node.js 20 o superior, un proyecto de Supabase y una clave de Gemini (nivel gratuito).

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS o Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # completa GEMINI_API_KEY, DATABASE_URL, SUPABASE_URL y SUPABASE_SECRET_KEY
alembic upgrade head              # crea las tablas en Supabase
python -m app.bootstrap           # cuentas de prueba → backend/credenciales_demo.txt
uvicorn app.main:app --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
copy .env.example .env.local      # URL de la API, URL de Supabase y clave publishable
npm run dev
```

Abre http://localhost:3000 e ingresa con alguna cuenta de `credenciales_demo.txt`.

### Pruebas

```bash
cd backend && pytest -q && ruff check app tests
cd frontend && npm run lint && npx tsc --noEmit
```

Las pruebas no llaman a Gemini ni a Supabase: usan dobles locales y tokens firmados con una clave ECC de prueba.

## Recorrido de la demo

1. **Coordinación:** revisa la institución, los docentes y las aulas.
2. **Docente:** entra al aula 3.º B y a la ficha de un estudiante, y genera la **prueba inicial**. En **Validación** la revisa y la aprueba.
3. **Estudiante:** entra con su usuario y su PIN y rinde la prueba. El Agente de Diagnóstico crea su perfil.
4. **Docente:** pide un material (por ejemplo, «fracciones»), lo **devuelve con una observación**, ve cómo se regenera y lo aprueba.
5. **Estudiante:** lee el material, consulta al asistente y responde marcando su confianza. Recibe la retroalimentación del Evaluador.
6. **Docente:** revisa la actividad del Agente de Refuerzo Conceptual (si hubo errores con mucha seguridad), el siguiente material que propuso el Orquestador, el semáforo, las alertas y la **Trazabilidad**.

## Estructura de la entrega

| Elemento | Contenido |
| --- | --- |
| `Presentacion_Final.pptx` | Presentación final (pendiente de subir) |
| `Video_Demostrativo.mp4` | Video demostrativo (pendiente de subir) |
| [`Diagramas/`](Diagramas) | Diagramas AS-IS, TO-BE, arquitectura, pipeline CI/CD, IoT, flujos y arquitectura integral |
| [`Prototipo/`](Prototipo) | Mando de respuestas en Wokwi y enlaces a la plataforma y a Isla Aprende |
| [`Evidencias/`](Evidencias) | Capturas de DevOps, banco de prompts, IoT, Make, Isla Aprende y plataforma desplegada |
| [`Repositorio_GitHub.txt`](Repositorio_GitHub.txt) | Enlaces al repositorio y a los despliegues |
| [`backend/`](backend) y [`frontend/`](frontend) | Código de la plataforma multiagente |

## Integrantes

- Airton Milton Giuseppi Saavedra Atoche
- Josue Abrham Ayala Valladolid
- Sebastian Delmy Neyra Pinaud
- Fabiana Sofia Diaz Saenz
- Fabiana Gerónimo Ormeño
- Steffano Jose Arnao Llavilla

Curso: Herramientas de Desarrollo Profesional TIC · Docente: Eleodoro Orbegoso Carrera · Facultad de Ingeniería, 2026.
