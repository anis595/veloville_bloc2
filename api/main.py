from fastapi import FastAPI

from api.routers import auth

app = FastAPI(title="VéloVille", version="0.1.0")
app.include_router(auth.router)


@app.get("/sante", tags=["Supervision"])
def sante():
    return {"statut": "ok"}
