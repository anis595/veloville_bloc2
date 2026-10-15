from fastapi import FastAPI

from api.routers import auth, incidents, stations, trajets

app = FastAPI(title="VéloVille", version="0.1.0")
for routeur in [auth, stations, trajets, incidents]:
    app.include_router(routeur.router)


@app.get("/sante", tags=["Supervision"])
def sante():
    return {"statut": "ok"}
