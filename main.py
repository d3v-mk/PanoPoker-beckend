from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from routers.routes import router

app = FastAPI()

@app.get("/")
def read_root():
    return {"msg": "Bem-vindo ao PanoPoker!"}

# Centraliza as rotas
app.include_router(router)

# Swagger JWT
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="PanoPoker API",
        version="1.0.0",
        description="API do PanoPoker",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return openapi_schema

app.openapi = custom_openapi
