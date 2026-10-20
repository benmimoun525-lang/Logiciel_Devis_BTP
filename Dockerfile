FROM python:3.10-slim

WORKDIR /app

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source complet
COPY . .

# Hugging Face Spaces écoute obligatoirement sur le port 7860
ENV PORT=7860
EXPOSE 7860

# Lancement du serveur FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
