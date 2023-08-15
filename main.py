from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn


from api import redis_api
from api import gdal_api

app = FastAPI(title="WMS Demo",
                      description="Demo using fastapi and mapscript to server OGC WMS",
                      version="0.0.1",)
redis = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_PROCESSING_SECOND = 600

def configure():
    configure_routing()
    # configure_api_keys()
    # configure_fake_data()


def configure_routing():
    # app.mount("/static", StaticFiles(directory="/app/static"), name="static")
    # app.mount("/download", StaticFiles(directory="/app/download"), name="download")
    app.include_router(redis_api.router)
    app.include_router(gdal_api.router)


if __name__ == "__main__":
    configure()
    uvicorn.run(app, port=8000, host="0.0.0.0")
else:
    configure()