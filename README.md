# Smart City Incident Reporting System

A web application for civic incident management. Citizens report infrastructure problems, the system routes them to the responsible municipal department, workers resolve them, and administrators oversee the entire pipeline. The application supports real-time status updates over WebSocket and automatic escalation of overdue incidents via a background scheduler.

**Live deployment:** https://smartcity-vxqp.onrender.com

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Application Modules](#application-modules)
- [Database Schema](#database-schema)
- [Real-Time System](#real-time-system)
- [Background Scheduling](#background-scheduling)
- [Role-Based Access Control](#role-based-access-control)
- [Incident Lifecycle](#incident-lifecycle)
- [API Endpoints](#api-endpoints)
- [Deployment](#deployment)
- [Local Development Setup](#local-development-setup)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)

---

## Architecture Overview

```
                        ┌─────────────────────────────────────┐
                        │            Browser Client            │
                        │   HTTP requests + WebSocket (wss)    │
                        └────────────┬──────────┬─────────────┘
                                     │          │
                            HTTP     │          │  WebSocket
                                     │          │
                        ┌────────────▼──────────▼─────────────┐
                        │         Render (ASGI / Daphne)       │
                        │                                      │
                        │  ┌──────────────────────────────┐   │
                        │  │       Django Application      │   │
                        │  │                              │   │
                        │  │  ProtocolTypeRouter          │   │
                        │  │  ├── HTTP → Django Views     │   │
                        │  │  └── WS   → Channels         │   │
                        │  │             Consumers         │   │
                        │  └──────────────────────────────┘   │
                        └───────────┬──────────────┬──────────┘
                                    │              │
                    ┌───────────────▼──┐    ┌──────▼───────────────┐
                    │  Supabase (PG)   │    │    Redis             │
                    │  PostgreSQL DB   │    │    Channel Layer      │
                    │  (SSL required)  │    │    (pub/sub)          │
                    └──────────────────┘    └──────────────────────┘
```

```
Real-Time Broadcast Flow
─────────────────────────

  Worker / Scheduler
       │
       │ HTTP POST or management command
       ▼
  StatusUpdate.save()
       │
       │ Django post_save signal
       ▼
  broadcast_status_update()
       │
       │ async_to_sync → channel_layer.group_send
       ▼
     Redis ──► group: 'incidents_live'
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
      Browser1  Browser2  Browser3
      (toast)   (toast)   (toast)
```

```
Auto-Escalation Flow
─────────────────────

  APScheduler (background thread, every 1 hour)
       │
       ▼
  escalate_incidents management command
       │
       ├── Query: deadline < now, status NOT IN [RESOLVED, ESCALATED]
       │
       ├── For each overdue incident:
       │      status   → ESCALATED
       │      priority → EMERGENCY
       │      save()
       │      StatusUpdate.create(updated_by=None)
       │
       └── post_save signal fires → Redis → WebSocket push to all browsers
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Web Framework | Django 4.2+ | HTTP request handling, ORM, admin, auth |
| ASGI Server | Daphne (via `channels[daphne]`) | Serves both HTTP and WebSocket connections |
| WebSocket | Django Channels | Async consumer-based WebSocket handling |
| Channel Layer | channels-redis + Redis | Pub/sub broker for cross-process WebSocket broadcast |
| Database | PostgreSQL (Supabase) | Primary data store, SSL enforced |
| ORM Driver | psycopg2-binary | PostgreSQL adapter for Django |
| Scheduler | APScheduler + django-apscheduler | Background interval job for auto-escalation |
| Static Files | WhiteNoise | Compressed static file serving without a separate web server |
| Image Handling | Pillow | Incident photo upload and storage |
| Environment | python-dotenv | `.env` file loading for local development |
| Frontend Maps | Leaflet.js + OpenStreetMap | Interactive map for incident geolocation |
| Frontend Charts | Chart.js | Analytics visualisations (bar, pie, line, heatmap) |
| CSS Framework | Bootstrap 5 | Responsive UI components |
| Deployment | Render | Cloud platform with HTTPS, environment variable management |

---

## Project Structure

```
SmartCityGit/
├── manage.py
├── requirements.txt
├── .env                        # local secrets (not committed)
│
├── smartcity/                  # project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py                 # ASGI entry point (HTTP + WebSocket routing)
│   └── wsgi.py
│
├── accounts/                   # user authentication and profile management
│   ├── models.py               # custom User model (extends AbstractUser)
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   ├── admin.py
│   └── migrations/
│
├── incidents/                  # core incident logic
│   ├── models.py               # Department, Incident, StatusUpdate
│   ├── views.py                # report, detail, my_incidents, JSON APIs
│   ├── forms.py
│   ├── urls.py
│   ├── admin.py
│   ├── consumers.py            # WebSocket consumer
│   ├── routing.py              # WebSocket URL patterns
│   ├── signals.py              # post_save broadcast trigger
│   ├── scheduler.py            # APScheduler setup
│   ├── apps.py                 # scheduler startup guard
│   ├── migrations/
│   └── management/
│       └── commands/
│           ├── setup_departments.py
│           └── escalate_incidents.py
│
├── dashboard/                  # views for public, admin, worker, analytics
│   ├── views.py
│   ├── urls.py
│   └── migrations/
│
├── templates/
│   ├── base.html
│   ├── accounts/
│   │   ├── login.html
│   │   ├── register.html
│   │   └── profile.html
│   ├── incidents/
│   │   ├── report.html
│   │   ├── detail.html
│   │   └── my_incidents.html
│   └── dashboard/
│       ├── public.html
│       ├── admin_panel.html
│       ├── worker_panel.html
│       └── analytics.html
│
└── static/
    ├── css/
    │   └── main.css
    └── js/
        ├── map.js              # Leaflet map interaction and geolocation
        ├── charts.js           # Chart.js rendering for analytics
        └── websocket.js        # WebSocket client with auto-reconnect
```

---

## Application Modules

### `smartcity/` — Project Configuration

**`settings.py`** manages all configuration through environment variables. Notable decisions:

- The Redis channel layer connection is tested at startup with a `ping()`. If Redis is unavailable, the application falls back to `InMemoryChannelLayer` automatically — WebSocket broadcasts work within a single process but not across multiple workers.
- `SECURE_PROXY_SSL_HEADER` is set to `("HTTP_X_FORWARDED_PROTO", "https")` because Render places a reverse proxy in front of the application. Without this, Django would not detect HTTPS correctly and would reject secure cookie assertions.
- `CSRF_COOKIE_SECURE` and `SESSION_COOKIE_SECURE` are enabled only when `DEBUG=False`, so local development does not require HTTPS.

**`asgi.py`** uses `ProtocolTypeRouter` to split traffic by protocol. HTTP traffic is handled by the standard Django ASGI application. WebSocket connections are routed through `AuthMiddlewareStack`, which populates `scope['user']` from the Django session, then dispatched to `IncidentConsumer` via the URL patterns in `incidents/routing.py`.

---

### `accounts/` — Authentication

Extends Django's `AbstractUser` with three additional fields:

| Field | Type | Notes |
|---|---|---|
| `role` | CharField | `citizen`, `admin`, or `worker`. Default: `citizen` |
| `phone` | CharField | Optional contact number |
| `department` | ForeignKey | Links workers to their assigned department. Null for citizens and admins |

Helper methods `is_citizen()`, `is_admin_user()`, and `is_worker()` are used throughout views to control access without hardcoding role string comparisons each time.

---

### `incidents/` — Core Logic

The primary application module. Contains all domain models, the WebSocket consumer, the signal broadcaster, the background scheduler, and the management commands.

---

### `dashboard/` — Views Layer

Contains no models. All views query the `incidents` app models directly. Separated from `incidents` to keep the incident module focused on business logic and keep presentation concerns isolated.

---

## Database Schema

```
accounts_user
─────────────────────────────────────────────────
id              BigAutoField  PK
username        VARCHAR(150)  unique
email           VARCHAR(254)
password        VARCHAR(128)
first_name      VARCHAR(150)
last_name       VARCHAR(150)
role            VARCHAR(10)   citizen | admin | worker
phone           VARCHAR(15)
department_id   FK → incidents_department (nullable)
is_staff        BOOLEAN
is_active       BOOLEAN
date_joined     TIMESTAMPTZ
last_login      TIMESTAMPTZ


incidents_department
─────────────────────────────────────────────────
id              BigAutoField  PK
name            VARCHAR(100)
code            VARCHAR(50)   unique  (PUBLIC_WORKS | SANITATION | ELECTRICITY | WATER | TRAFFIC)
email           VARCHAR(254)
phone           VARCHAR(15)
description     TEXT


incidents_incident
─────────────────────────────────────────────────
id              BigAutoField  PK
tracking_id     VARCHAR(20)   unique  (INC-XXXXXXXX, auto-generated)
title           VARCHAR(200)
description     TEXT
incident_type   VARCHAR(20)   POTHOLE | GARBAGE | STREETLIGHT | WATER_LEAK | TRAFFIC | MISC
status          VARCHAR(20)   SUBMITTED | ASSIGNED | IN_PROGRESS | RESOLVED | ESCALATED
priority        VARCHAR(10)   LOW | MEDIUM | HIGH | EMERGENCY
latitude        DECIMAL(9,6)
longitude       DECIMAL(9,6)
address         VARCHAR(255)
area            VARCHAR(100)
image           ImageField    uploads to media/incidents/
reported_by_id  FK → accounts_user
assigned_to_id  FK → accounts_user (nullable)
department_id   FK → incidents_department (nullable)
created_at      TIMESTAMPTZ   auto_now_add
updated_at      TIMESTAMPTZ   auto_now
resolved_at     TIMESTAMPTZ   nullable, set when status → RESOLVED
deadline        TIMESTAMPTZ   auto-calculated from priority on save


incidents_statusupdate
─────────────────────────────────────────────────
id              BigAutoField  PK
incident_id     FK → incidents_incident
status          VARCHAR(20)
note            TEXT
updated_by_id   FK → accounts_user (nullable, NULL = system action)
timestamp       TIMESTAMPTZ   auto_now_add
```

**Automatic logic in `Incident.save()`:**

1. Generates `tracking_id` (`INC-` + 8 random uppercase characters) if the record is new.
2. Routes to the appropriate department based on `incident_type` using a static mapping dict (`DEPT_ROUTING`).
3. Calculates and sets `deadline` based on `priority` using `timedelta`:
   - `EMERGENCY` → 2 hours
   - `HIGH` → 24 hours
   - `MEDIUM` → 72 hours
   - `LOW` → 168 hours
4. For `EMERGENCY` priority, auto-assigns to the first available worker in the matched department.

---

## Real-Time System

The real-time update system is built on Django Channels with Redis as the channel layer backend. It delivers incident status changes to all connected browsers without polling.

### Components

**`incidents/routing.py`**

Maps the WebSocket path to the consumer, equivalent to `urls.py` for HTTP:

```
ws://host/ws/incidents/  →  IncidentConsumer
```

**`incidents/consumers.py` — `IncidentConsumer`**

An `AsyncWebsocketConsumer` that manages browser connections:

- `connect()` — adds the socket to the `incidents_live` channel group and accepts the handshake.
- `disconnect()` — removes the socket from the group, preventing broadcast to dead connections.
- `receive()` — intentionally empty. Clients are receive-only. All state-changing operations go through authenticated HTTP POST views.
- `incident_update()` — called by the channel layer when a message of type `incident.update` is sent to the group. Serialises the payload and pushes it to the browser.

The method name `incident_update` corresponds to the message type `incident.update` — Django Channels replaces dots with underscores when dispatching.

**`incidents/signals.py` — `broadcast_status_update`**

A `post_save` receiver on `StatusUpdate`. Fires only on creation (`if not created: return`). Constructs a JSON-serialisable payload and calls `channel_layer.group_send()` to deliver it to every socket in `incidents_live`.

`async_to_sync` is required because Django signals execute in synchronous context, while `group_send` is a coroutine.

If the channel layer is `None` (Redis unavailable), the broadcast is silently skipped — no exception is raised and the save operation completes normally.

**`static/js/websocket.js` — Browser Client**

- Selects `ws://` or `wss://` based on the page protocol, so the same file works in development and production.
- On `onmessage`: displays a Bootstrap toast notification and calls `window.onIncidentUpdate(data)` if defined by the current page — each template can define its own handler for DOM updates.
- Implements exponential backoff on `onclose`: retries at 3 s, 4.5 s, 6.75 s, ... capped at 30 s. This prevents connection storms after a server restart.

### Message Payload

```json
{
  "incident_id": 42,
  "tracking_id": "INC-A3F8B2C1",
  "title": "Broken streetlight on MG Road",
  "status": "IN_PROGRESS",
  "status_display": "In Progress",
  "note": "Crew dispatched, repair scheduled for tomorrow.",
  "updated_by": "worker_ravi",
  "timestamp": "2026-04-08T14:30:00+05:30"
}
```

---

## Background Scheduling

**`incidents/scheduler.py`**

Uses APScheduler's `BackgroundScheduler`, which runs in a separate daemon thread inside the Django process. The `DjangoJobStore` persists job metadata (last run time, next run time) to the database, making it visible in the Django admin interface.

The `escalate_incidents` job is registered with `replace_existing=True`. On server restart, the existing job record in the database is updated rather than creating a duplicate.

**`incidents/apps.py` — Startup Guard**

The scheduler is started in `IncidentsConfig.ready()`. Without a guard, running any management command (e.g., `migrate`) would also start the scheduler, which attempts to query `django_apscheduler` tables that may not yet exist. The guard inspects `sys.argv` and skips scheduler startup for a defined list of commands.

**`incidents/management/commands/escalate_incidents.py`**

Queries all incidents where `deadline < now` and `status` is not `RESOLVED` or `ESCALATED`. For each:

- Sets `status = ESCALATED` and `priority = EMERGENCY`.
- Ensures a department is assigned (catches any unrouted `MISC` incidents).
- Creates a `StatusUpdate` with `updated_by=None` (displayed as "System" in the UI).

Because `StatusUpdate` creation fires the `post_save` signal, the escalation automatically triggers a WebSocket broadcast to all connected browsers — no additional code required.

---

## Role-Based Access Control

| Action | Citizen | Worker | Admin |
|---|---|---|---|
| View public dashboard | Yes | Yes | Yes |
| Report an incident | Yes | No | No |
| View own incidents | Yes | — | — |
| View assigned incidents | — | Yes | — |
| View all incidents | No | No | Yes |
| Update incident status | No | Yes (assigned only) | Yes |
| Access admin panel | No | No | Yes |
| Access worker panel | No | Yes | No |
| View analytics | No | Yes | Yes |

Access control is enforced in views using the `is_citizen()`, `is_admin_user()`, and `is_worker()` methods on the user model. Views redirect unauthorized users rather than returning 403 responses for most page views. The `update_status_api` JSON endpoint returns an explicit `403` for citizens.

---

## Incident Lifecycle

```
  Citizen submits report
          │
          ▼
     [SUBMITTED]
          │
          │  Admin assigns to department/worker
          ▼
     [ASSIGNED]
          │
          │  Worker begins work
          ▼
    [IN_PROGRESS]
          │
          ├──────────────────────────────┐
          │                              │
          │  Worker marks complete       │  Deadline exceeded (scheduler)
          ▼                              ▼
     [RESOLVED]                    [ESCALATED]
      resolved_at set               priority → EMERGENCY
                                    WebSocket push to all browsers
```

Every transition creates an immutable `StatusUpdate` record, building a full audit trail visible on the incident detail page.

---

## API Endpoints

### HTTP

| Method | URL | Auth | Description |
|---|---|---|---|
| GET | `/` | None | Public dashboard |
| GET | `/admin-panel/` | Admin | All incidents with filters |
| GET | `/worker-panel/` | Worker | Assigned incidents |
| GET | `/analytics/` | Admin / Worker | Chart data views |
| GET / POST | `/report/` | Citizen | Submit new incident |
| GET / POST | `/incidents/<id>/` | Any | Incident detail + status update form |
| GET | `/my-incidents/` | Citizen | Incidents reported by current user |
| GET | `/api/incidents/` | None | Filtered JSON list of incidents |
| POST | `/api/incidents/<id>/status/` | Admin / Worker | Update incident status (JSON) |
| GET / POST | `/register/` | None | User registration |
| GET / POST | `/login/` | None | User login |
| POST | `/logout/` | Authenticated | User logout |
| GET / POST | `/profile/` | Authenticated | Edit profile |

### WebSocket

| URL | Description |
|---|---|
| `wss://host/ws/incidents/` | Subscribe to live incident status updates |

The WebSocket endpoint is receive-only from the client side. All messages flow server-to-client.

### `GET /api/incidents/` Query Parameters

| Parameter | Values | Description |
|---|---|---|
| `status` | `SUBMITTED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `ESCALATED` | Filter by status |
| `type` | `POTHOLE`, `GARBAGE`, `STREETLIGHT`, `WATER_LEAK`, `TRAFFIC`, `MISC` | Filter by incident type |
| `area` | string | Case-insensitive substring match on area field |
| `q` | string | Search across title, tracking ID, and area |

Results are sorted by priority rank (EMERGENCY first), then deadline ascending, then creation date descending. Priority ranking uses a Django `Case/When` annotation to assign numeric sort weights at the database level.

---

## Deployment

The application is deployed on **Render** using the ASGI server Daphne (included via `channels[daphne]`). Daphne handles both HTTP and WebSocket connections on the same port.

**Build command (runs before each deploy):**
```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

**Start command:**
```bash
daphne smartcity.asgi:application --bind 0.0.0.0 --port $PORT
```

**Database:** Supabase-hosted PostgreSQL. The connection string uses the Supabase connection pooler endpoint (`pooler.supabase.com`) with `sslmode=require`.

**Static files:** `collectstatic` copies all static files into `staticfiles/`. WhiteNoiseMiddleware serves them directly from Django with `Cache-Control` headers and Brotli/gzip compression. No separate CDN or web server is required.

**Media files:** Incident photos are stored in `media/incidents/` on the server's local filesystem. On Render's free tier, the filesystem is ephemeral — uploaded images are lost on redeploy. For persistent media storage, an object storage service (S3 or equivalent) should be configured via `django-storages`.

**Security headers active in production (`DEBUG=False`):**
- `CSRF_COOKIE_SECURE = True`
- `SESSION_COOKIE_SECURE = True`
- `SECURE_PROXY_SSL_HEADER` — detects HTTPS from the Render proxy's `X-Forwarded-Proto` header
- `SECURE_REFERRER_POLICY = 'no-referrer-when-downgrade'`

---

## Local Development Setup

**Prerequisites:** Python 3.10+, PostgreSQL, Redis (optional)

```bash
git clone <repository-url>
cd SmartCityGit

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env              # fill in your local values
```

```bash
python manage.py migrate
python manage.py setup_departments
python manage.py createsuperuser

python manage.py runserver
```

If Redis is not running locally, the application falls back to `InMemoryChannelLayer`. WebSocket broadcasts work within a single process in this mode — sufficient for development.

To test WebSocket behaviour with Redis:
```bash
redis-server                       # in a separate terminal
python manage.py runserver
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key. Must be long, random, and kept private. |
| `DEBUG` | Yes | `True` for development, `False` for production. |
| `ALLOWED_HOSTS` | Yes | Comma-separated list of valid hostnames. |
| `CSRF_TRUSTED_ORIGINS` | Yes | Comma-separated list of trusted origins for CSRF (include `https://`). |
| `DB_NAME` | Yes | PostgreSQL database name. |
| `DB_USER` | Yes | PostgreSQL user. |
| `DB_PASSWORD` | Yes | PostgreSQL password. |
| `DB_HOST` | Yes | PostgreSQL host. |
| `DB_PORT` | No | PostgreSQL port. Default: `5432`. |
| `REDIS_URL` | No | Redis connection URL. Default: `redis://127.0.0.1:6379`. Falls back to in-memory layer if unavailable. |

---

## Database Migrations

Migrations are version-controlled and applied in order.

| App | Migration | Change |
|---|---|---|
| `accounts` | `0001_initial` | Creates the custom `User` table with `role` and `phone` fields |
| `accounts` | `0002_initial` | Adds `department` ForeignKey from `User` to `Department` |
| `incidents` | `0001_initial` | Creates `Department`, `Incident`, and `StatusUpdate` tables |
| `incidents` | `0002_add_misc_incident_type` | Adds `MISC` as a sixth incident type for unclassified reports |
| `incidents` | `0003_remove_closed_status` | Removes the `CLOSED` status choice, standardising on `RESOLVED` and `ESCALATED` |

On a fresh database, run:
```bash
python manage.py migrate
python manage.py setup_departments
```

`setup_departments` uses `update_or_create` — it is safe to run multiple times and will not create duplicate department records.
