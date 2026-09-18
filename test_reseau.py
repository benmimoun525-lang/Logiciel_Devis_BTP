import socket
import sys

def check_port(host="127.0.0.1", port=8000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex((host, port))
    sock.close()
    if result == 0:
        print(f"[OK] Le port {port} sur {host} est OUVERT et accessible.")
        return True
    else:
        print(f"[ERREUR] Impossible de se connecter à {host}:{port} (Code erreur: {result}).")
        return False

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=== DIAGNOSTIC RESEAU FASTAPI ===")
    print(f"Adresse IP locale détectée : {local_ip}")
    print("-" * 35)
    
    print("1. Test de boucle locale (localhost)...")
    check_port("127.0.0.1", 8000)
    
    print("\n2. Test sur l'adresse IP réseau locale...")
    check_port(local_ip, 8000)