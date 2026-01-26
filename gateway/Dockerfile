# Gateway IAM - Dockerfile
# Interface Python FastAPI entre MidPoint, N8N, PostgreSQL et Supabase

FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY . .

# Créer un utilisateur non-root
RUN useradd -m -u 1000 gateway
USER gateway

# Exposer le port
EXPOSE 8000

# Variables d'environnement par défaut
ENV APP_ENV=production
ENV APP_DEBUG=false
ENV APP_PORT=8000

# Commande de démarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

