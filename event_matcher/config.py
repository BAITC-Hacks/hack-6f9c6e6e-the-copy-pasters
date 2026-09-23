from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data.csv"


def _load_local_env() -> None:
    """Load simple KEY=VALUE settings without overriding process environment."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if name and name not in os.environ:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ[name] = value


_load_local_env()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")

REQUIRED_COLUMNS = {
    "id", "anon_name", "categories", "city", "city_imputed", "synthetic",
    "price_from_kzt", "price_imputed", "event_formats", "languages",
    "max_hours", "busy_dates", "description",
}

QUERY_TERMS = {
    "свадьба": {"свадьб", "той", "невест", "жених", "wedding"},
    "той": {"той", "свадьб", "торжеств"},
    "корпоратив": {"корпоратив", "компан", "команд", "бизнес", "company"},
    "конференция": {"конференц", "форум", "делов", "conference"},
    "юбилей": {"юбиле", "торжеств", "anniversary"},
    "день рождения": {"рождени", "именин", "birthday"},
    "ведущий": {"ведущ", "тамад", "ведени", "host", "mc"},
    "фотограф": {"фотограф", "съемк", "съёмк", "фотосесс", "photo"},
    "видеограф": {"видеограф", "видеосъем", "видеосъём", "видео", "video"},
    "флорист": {"флорист", "цвет", "букет", "оформлен", "декор"},
    "декоратор": {"декорат", "оформлен", "цвет", "декор"},
    "банкетный зал": {"банкет", "зал", "ресторан", "площадк", "venue"},
}
