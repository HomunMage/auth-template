# main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from router.auth import router as auth_router

app = FastAPI(title="Auth Template API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("BACKEND_PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
