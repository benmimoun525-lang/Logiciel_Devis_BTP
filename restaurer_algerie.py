import subprocess
import sys
import os

print("=" * 70)
print("  RESTAURATION FORCÉE DE LA VERSION ALGÉRIE (M. BENABDALLAH)")
print("=" * 70)
print()

# Trouver le chemin de git si pas dans PATH
git_cmd = "git"
possible_git = [
    r"C:\Program Files\Git\cmd\git.exe",
    r"C:\Program Files\Git\bin\git.exe",
    r"C:\Program Files (x86)\Git\cmd\git.exe",
    r"C:\Program Files (x86)\Git\bin\git.exe",
    r"C:\Git\cmd\git.exe",
    r"C:\Git\bin\git.exe",
    os.path.expandvars(r"%LocalAppData%\Programs\Git\cmd\git.exe"),
    os.path.expandvars(r"%LocalAppData%\Programs\Git\bin\git.exe"),
    os.path.expandvars(r"%ProgramFiles%\Git\cmd\git.exe"),
    os.path.expandvars(r"%ProgramFiles%\Git\bin\git.exe")
]
for p in possible_git:
    if os.path.exists(p):
        git_cmd = p
        break

print(f"[*] Utilisation de Git : {git_cmd}")

# Sauvegarder la version Europe dans index_europe.html si présente
if os.path.exists("index.html"):
    try:
        with open("index.html", "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read(500)
            if "Version Europe" in txt:
                with open("index.html", "rb") as f_in, open("index_europe.html", "wb") as f_out:
                    f_out.write(f_in.read())
                print("[*] Version Europe mise de côté dans 'index_europe.html'.")
    except Exception as e:
        print(f"[*] Note sauvegarde Europe: {e}")

found = False
candidates = []

# 1. Parcourir les commits Git récents
try:
    res = subprocess.run([git_cmd, "log", "-n", "40", "--format=%H"], capture_output=True, text=True)
    if res.returncode == 0:
        candidates.extend(res.stdout.strip().splitlines())
except Exception as e:
    print(f"[!] Erreur git log: {e}")

# 2. Ajouter reflog
try:
    res_ref = subprocess.run([git_cmd, "reflog", "-n", "40", "--format=%H"], capture_output=True, text=True)
    if res_ref.returncode == 0:
        for c in res_ref.stdout.strip().splitlines():
            if c not in candidates:
                candidates.append(c)
except Exception:
    pass

# Commits connus
known_commits = ["4a9bff2", "38ed851", "HEAD~1", "HEAD~2", "HEAD~3", "HEAD~4", "main~1", "main~2"]
for kc in known_commits:
    if kc not in candidates:
        candidates.append(kc)

print(f"[*] Analyse de {len(candidates)} versions de l'historique...")

for c in candidates:
    if not c.strip():
        continue
    try:
        show_res = subprocess.run([git_cmd, "show", f"{c.strip()}:index.html"], capture_output=True)
        content = show_res.stdout
        if len(content) > 100000 and (b"BENABDALLAH" in content or b"BaridiMob" in content or b"00799999000191804708" in content):
            print()
            print(f"✅ VERSION ALGÉRIE TROUVÉE dans le commit {c[:10]} !")
            print(f"   Taille : {len(content):,} octets ({len(content.splitlines()):,} lignes)")
            
            with open("index.html", "wb") as f:
                f.write(content)
            with open("index_algerie.html", "wb") as f:
                f.write(content)
                
            print("   -> Fichier 'index.html' restauré avec succès !")
            print("   -> Copie de sécurité 'index_algerie.html' créée !")
            found = True
            break
    except Exception as err:
        continue

if not found:
    print()
    print("❌ Aucune version correspondante trouvée directement.")
    print("Détails des derniers commits disponibles :")
    try:
        l = subprocess.run([git_cmd, "log", "-n", "5", "--oneline"], capture_output=True, text=True)
        print(l.stdout)
    except Exception:
        pass
else:
    print()
    print("=" * 70)
    print("  [SUCCÈS TOTAL] VOTRE LOGICIEL ALGÉRIE EST RESTAURÉ DANS index.html !")
    print("=" * 70)
    print("  Titulaire : BOUFELDJA BENABDALLAH")
    print("  BaridiMob : 00799999000191804708")
    print("  Devise    : Dinars Algériens (DZD)")
    print("=" * 70)
