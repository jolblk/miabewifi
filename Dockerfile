# ---- Étape 1 : build du frontend React ----
FROM node:24-slim AS frontend-build
WORKDIR /src
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# ---- Étape 2 : image Python qui sert l'API + le build React ----
FROM python:3.13-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app
COPY alembic/ ./alembic
COPY alembic.ini .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

COPY --from=frontend-build /src/app/static/dist ./app/static/dist

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]