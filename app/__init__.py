from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.config import config
from app.functions.handlers import logger_exception_handler
from app.functions.middleware import add_process_time_header, lifespan

app = FastAPI(lifespan=lifespan)

# CORS middleware - must be added before other middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        config.FRONTEND_URL,
        "http://localhost:3000",  # Fallback for dev
        "http://127.0.0.1:3000",  # Fallback for dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(add_process_time_header)
app.add_middleware(CorrelationIdMiddleware, header_name="X-Correlation-ID")
app.exception_handler(HTTPException)(logger_exception_handler)

app.include_router(api_router)
