from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import DATA_PATH, PROJECT_ROOT
from ..repositories.catalog import load_catalog
from .routes import router


STATIC_DIR = PROJECT_ROOT / "static"


def create_app(catalog_path: Path = DATA_PATH) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.catalog = load_catalog(catalog_path)
        except (FileNotFoundError, ValueError) as error:
            raise RuntimeError(f"Не удалось загрузить каталог: {error}") from error
        yield

    app = FastAPI(title="EventMatch KZ", lifespan=lifespan)
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")

    @app.get("/", include_in_schema=False)
    def homepage():
        return FileResponse(STATIC_DIR / "index.html")

    return app
