from fastapi import FastAPI

from api.routers import auth, incidents, indicateurs, stations, trajets

app = FastAPI(title="VéloVille", version="1.0.0")
for routeur in [auth, stations, trajets, incidents, indicateurs]:
    app.include_router(routeur.router)


@app.get("/sante", tags=["Supervision"])
def sante():
    return {"statut": "ok"}
