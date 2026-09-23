# Архитектура EventMatch KZ

## Компоненты

```text
Браузер: static/index.html + css/styles.css + js/app.js/auth.js/providers.js/ai.js
             │ same-origin JSON + пользовательский bearer token
             ▼
FastAPI: app.py → api/application.py → api/routes.py → api/schemas.py
             ├→ repositories/catalog.py → data.csv (общий каталог)
             ├→ repositories/supabase.py → Supabase Auth + PostgREST (JWT + RLS)
             ├→ services/providers.py → личные профили для подбора
             ├→ services/matching.py → фильтры → стабильное ранжирование → top 3
             └→ services/ai_analysis.py → OpenAI Responses API (только по кнопке)
```

- `app.py` — точка входа Uvicorn; `api/application.py` загружает CSV и отдаёт страницу.
- `api/routes.py` отвечает за справочники, поиск, Supabase Auth, личные профили и ИИ-анализ. `api/schemas.py` валидирует входные данные.
- `repositories/catalog.py` читает исходный CSV. `repositories/supabase.py` обращается к Auth и PostgREST через publishable key и пользовательский JWT, поэтому доступ к строкам ограничивается RLS.
- `services/providers.py` преобразует личные профили в записи каталога, не изменяя `data.csv`.
- `services/matching.py` выполняет жёсткую фильтрацию и стабильное ранжирование. `services/relevance.py` оценивает релевантность описания; `services/explanations.py` объясняет совпадение фактами.
- `services/ai_analysis.py` отправляет выбранный профиль в OpenAI только после явного запроса. Ключ читается из `.env`; поиск и просмотр не зависят от ИИ.
- `static/js/auth.js`, `providers.js`, `ai.js` и `app.js` разделяют сессию, личный каталог, вызов ИИ и поиск.
- `supabase/migrations/` содержит SQL для таблицы личных профилей и RLS. Её нужно выполнить в Supabase SQL Editor.

## Потоки данных

```text
гость: data.csv → options → поиск → жёсткие фильтры → до 3 результатов
пользователь: data.csv + личные строки текущего JWT (RLS) → options/search
добавление: email/password → Supabase Auth → JWT → FastAPI → PostgREST → RLS(owner_id)
анализ: выбранный профиль + условия → кнопка → FastAPI → OpenAI Responses API
```

Пользовательские записи видны только владельцу. Клиент не передаёт доверенный `owner_id`: сервер получает его из проверенного Supabase Auth пользователя. Секретный Supabase key не используется.

## HTTP API

- `GET /api/config` сообщает только, настроены ли Supabase и OpenAI.
- `GET /api/options` возвращает справочники CSV и личных профилей текущей сессии; `city` ограничивает категории выбранным городом.
- `POST /api/match` фильтрует CSV и личные профили текущего пользователя по городу, дате, формату, категории, бюджету, языку и длительности.
- `POST /api/auth/signup`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/refresh`, `POST /api/auth/logout` управляют пользовательской сессией.
- `GET/POST /api/personal-providers`, `PUT/DELETE /api/personal-providers/{id}` — пользовательские CRUD операции, ограниченные RLS.
- `GET /api/providers/{id}` — подробный профиль CSV либо профиль владельца.
- `POST /api/providers/{id}/analysis` — ИИ-анализ одного выбранного профиля по кнопке.
- `matched` содержит максимум три результата. `no_category` означает отсутствие категории в городе. `filtered_out` возвращает счётчики причин исключения.

## Ранжирование и достоверность

Занятость на выбранный день, формат, бюджет, язык и длительность проверяются обычным кодом. Подходящие профили ранжируются по релевантности описания, цене и длительности; ID обеспечивает детерминированный порядок. ИИ не меняет фильтры или ранжирование.

Отсутствие выбранной даты в `busy_dates` означает только отсутствие отметки о занятости. Фактическую доступность требуется уточнить у подрядчика. Синтетические данные и восстановленные поля помечаются.

## Конфигурация

Корневой `.env` не коммитится. Минимальные настройки для личного хранилища: `SUPABASE_URL` и `SUPABASE_PUBLISHABLE_KEY`. Для ИИ дополнительно нужен `OPENAI_API_KEY`; модель по умолчанию — `gpt-6-luna`, её можно изменить через `OPENAI_MODEL`. SQL-миграция и настройка разрешённых Auth redirect URLs описаны в [README.md](README.md).
