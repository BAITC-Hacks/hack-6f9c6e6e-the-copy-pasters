# Личные подрядчики и ИИ-анализ: план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Добавить регистрацию, личные профили подрядчиков в Supabase, подробную карточку профиля и запрашиваемый пользователем ИИ-анализ.

**Architecture:** Гости продолжают искать в исходном CSV. Авторизованные пользователи получают личные операции с таблицей Supabase через серверный API и пользовательский JWT, с проверкой владельца в RLS. Серверный OpenAI-клиент читает ключ из `.env`; ИИ запускается только вручную и не участвует в фильтрации или ранжировании.

**Tech Stack:** FastAPI, Python stdlib HTTP client for Supabase Auth/PostgREST, OpenAI Python SDK, Supabase Auth and Postgres RLS, static HTML/CSS/JavaScript.

**Spec:** `docs/superpowers/specs/2026-09-23-personal-contractors-and-ai-design.md`

## Global Constraints

- Исходный `data.csv` остаётся общим каталогом и не меняется.
- Личные профили видит и изменяет только их владелец.
- Ключи остаются только в серверном `.env`, не отправляются браузеру и не попадают в логи или исходный код.
- ИИ-анализ отправляется только для выбранного профиля по явному действию пользователя.
- Существующие жёсткие фильтры и детерминированное ранжирование не зависят от ИИ.
- Внешние API не вызываются при старте приложения или обычном поиске.

## Review Focus

- Чужой, истёкший или поддельный access token: endpoint не возвращает личные данные.
- Несовпадающий `owner_id` или UUID: RLS и серверная проверка блокируют чтение/изменение чужой строки.
- Отключённая почтовая регистрация или неподтверждённый email: UI объясняет, что нужно подтвердить адрес.
- Пустой/неверный OpenAI ключ и сетевой отказ: поиск и карточка работают, ИИ показывает контролируемую ошибку.
- Длинные описания и поля со спецсимволами: API валидирует размеры, DOM строится через `textContent`.

## Files and responsibilities

- `event_matcher/config.py`: чтение `.env`, Supabase и OpenAI runtime settings.
- `event_matcher/services/supabase.py`: безопасные Auth/PostgREST HTTP-вызовы с пользовательским токеном.
- `event_matcher/services/ai_analysis.py`: ограниченный OpenAI запрос с проверяемым фактическим контекстом.
- `event_matcher/api/schemas.py`: модели регистрации, входа, личных профилей и анализа.
- `event_matcher/api/routes.py`: Auth, публичные детали, личные CRUD и AI endpoints.
- `event_matcher/api/application.py`: клиентские состояния и конфигурация приложения.
- `static/index.html`, `static/css/styles.css`, `static/js/app.js`: регистрация/вход, добавление, список личных записей, подробная карточка и анализ.
- `supabase/migrations/202609230001_personal_contractors.sql`: таблица, ограничения и RLS.
- `.env`, `.env.example`, `.gitignore`, `requirements.txt`: локальная конфигурация и зависимости.
- `README.md`, `ARCHITECTURE.md`: настройка Supabase, переменных окружения и потоков данных.

## Tasks

### Task 1: Configuration, Supabase migration, and API services

Implement dotenv loading without printing values; configure Supabase project URL and publishable key plus optional OpenAI API key and model. Add a server-side Supabase Auth/PostgREST client that forwards each user's bearer JWT and rejects requests when auth is not configured. Add a migration with owner-scoped personal contractor rows and RLS policies using `auth.uid()`. Add validated schemas and FastAPI endpoints for signup, login, current user, logout, public CSV details, personal list/create/update/delete. Never accept owner IDs from client input.

**Deliverable:** the API can authenticate and perform owner-scoped CRUD after the migration has been applied in Supabase.

### Task 2: On-demand AI analysis

Add an OpenAI client initialized only when `OPENAI_API_KEY` exists. Accept one bounded provider profile plus optional event criteria, set a concise Russian system instruction requiring evidence-only claims, cap input length and output tokens, and map provider/API failures to safe HTTP errors without exposing key or raw provider error details.

**Deliverable:** `POST /api/providers/{provider_id}/analysis` analyzes one validated CSV or owned profile only; no search code calls it.

### Task 3: Client account, provider details, personal profile management

Add email signup/login/logout, retain access token in session storage, attach it only to personal endpoints, and expose profile controls only while signed in. Make provider names open a semantic accessible dialog containing source fields and provenance tags. Add a labeled form to create and edit personal profiles and an owner-only delete action. Show a separate “ИИ-анализ” action and its result/status in the dialog. Build user-provided content with DOM text nodes, not HTML interpolation. Keep the design responsive and keyboard-operable.

**Deliverable:** a user can sign in, maintain private profiles, open either public or owned profile details, and request a factual AI analysis.

### Task 4: Setup documentation and manual integration review

Add `.env.example` without secrets; document where to paste local values, run the Supabase migration in SQL Editor, configure Auth email confirmation, start the server, and configure an API spend limit in OpenAI Platform. Document that the app remains usable without OpenAI but personal storage requires valid Supabase credentials and the migration. Review changes for secret leakage, unchanged CSV, clear empty/error states, and consistent endpoint names.

**Deliverable:** reproducible setup instructions and a clean implementation review. Automated tests are omitted because the user did not request test execution.
