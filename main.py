from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from api.auth import router as auth_router
from api.chat import router as chat_router
from api.session import router as session_router
from api.upload import router as upload_router

# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD", "PUT"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(session_router)
app.include_router(upload_router)

if __name__ == "__main__":
    import uvicorn
    # WARNING: Ensure to change host to "0.0.0.0" before deployment to expose the server externally.
    uvicorn.run(app, host="127.0.0.1", port=8000)
