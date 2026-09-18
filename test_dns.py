import socket

host = "generativelanguage.googleapis.com"

print(f"--- Test de résolution DNS pour {host} ---")
try:
    ip = socket.gethostbyname(host)
    print(f"SUCCESS: L'adresse IP de Google Gemini est : {ip}")
except socket.gaierror as e:
    print(f"ÉCHEC DNS [Errno 11001]: Impossible de trouver l'adresse IP. Erreur : {e}")