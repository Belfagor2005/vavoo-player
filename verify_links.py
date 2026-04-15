"""
Verifica i link della playlist M3U8
Testa un campione di canali per verificare che gli stream siano raggiungibili
"""
import re
import requests
# import time
# import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_AGENT = "okhttp/4.11.0"
TIMEOUT = 15
MAX_WORKERS = 10


def get_auth_signature():
    """Ottiene la signature per risolvere i link Vavoo."""
    url = "https://www.lokke.app/api/app/ping"
    headers = {
        "user-agent": USER_AGENT,
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip"
    }
    data = {
        "token": "ldCvE092e7gER0rVIajfsXIvRhwlrAzP6_1oEJ4q6HH89QHt24v6NNL_jQJO219hiLOXF2hqEfsUuEWitEIGN4EaHHEHb7Cd7gojc5SQYRFzU3XWo_kMeryAUbcwWnQrnf0-",
        "reason": "app-blur",
        "locale": "de",
        "theme": "dark",
        "metadata": {
            "device": {"type": "Handset", "brand": "google", "model": "Nexus", "name": "21081111RG", "uniqueId": "d10e5d99ab665233"},
            "os": {"name": "android", "version": "7.1.2", "abis": ["arm64-v8a"], "host": "android"},
            "app": {"platform": "android", "version": "1.1.0", "buildId": "97215000", "engine": "hbc85", "signatures": ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"], "installer": "com.android.vending"},
            "version": {"package": "app.lokke.main", "binary": "1.1.0", "js": "1.1.0"},
            "platform": {"isAndroid": True, "isIOS": False, "isTV": False, "isWeb": False, "isMobile": True, "isWebTV": False, "isElectron": False}
        },
        "appFocusTime": 0,
        "playerActive": False,
        "playDuration": 0,
        "devMode": True,
        "hasAddon": True,
        "castConnected": False,
        "package": "app.lokke.main",
        "version": "1.1.0",
        "process": "app",
        "firstAppStart": 1772388338206,
        "lastAppStart": 1772388338206,
        "ipLocation": None,
        "adblockEnabled": False,
        "proxy": {"supported": ["ss", "openvpn"], "engine": "openvpn", "ssVersion": 1, "enabled": False, "autoServer": True, "id": "fi-hel"},
        "iap": {"supported": True}
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=10, verify=False)
        return r.json().get("addonSig")
    except Exception as e:
        print(f"Errore autenticazione: {e}")
        return None


def resolve_vavoo_url(url, signature):
    """Risolve un URL Vavoo usando la signature."""
    headers = {
        "user-agent": "MediaHubMX/2",
        "accept": "application/json",
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip",
        "mediahubmx-signature": signature
    }
    data = {
        "language": "de",
        "region": "AT",
        "url": url,
        "clientVersion": "3.0.2"
    }
    try:
        r = requests.post("https://vavoo.to/mediahubmx-resolve.json", json=data, headers=headers, timeout=15, verify=False)
        result = r.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("url")
    except Exception as e:
        print(e)
        pass
    return None


def parse_playlist(path):
    """Parse M3U8 e ritorna lista di canali."""
    channels = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            # Extract name
            name_match = re.search(r',(.+)$', line)
            name = name_match.group(1).strip() if name_match else "Unknown"

            # Extract tvg-id
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
            tvg_id = tvg_id_match.group(1) if tvg_id_match else ""

            # Get URL
            url = lines[i + 1].strip() if i + 1 < len(lines) else ""

            if url and not url.startswith("#"):
                channels.append({
                    "name": name,
                    "tvg_id": tvg_id,
                    "url": url
                })
            i += 2
        else:
            i += 1
    return channels


def test_channel(channel, signature):
    """Testa un singolo canale."""
    name = channel["name"]
    url = channel["url"]

    # Se è un URL Vavoo, prova a risolverlo
    if "vavoo" in url.lower():
        resolved = resolve_vavoo_url(url, signature)
        if resolved:
            # Testa l'URL risolto
            try:
                r = requests.get(resolved, timeout=TIMEOUT, stream=True, verify=False)
                status = r.status_code
                r.close()
                return {
                    "name": name,
                    "status": status,
                    "ok": status < 400,
                    "resolved": True
                }
            except Exception as e:
                return {
                    "name": name,
                    "status": 0,
                    "ok": False,
                    "error": str(e),
                    "resolved": True
                }
        else:
            return {
                "name": name,
                "status": 0,
                "ok": False,
                "error": "Risoluzione fallita",
                "resolved": False
            }
    else:
        # URL diretto, testalo
        try:
            r = requests.get(url, timeout=TIMEOUT, stream=True, verify=False)
            status = r.status_code
            r.close()
            return {
                "name": name,
                "status": status,
                "ok": status < 400,
                "resolved": False
            }
        except Exception as e:
            return {
                "name": name,
                "status": 0,
                "ok": False,
                "error": str(e),
                "resolved": False
            }


def main():
    playlist_path = "playlist.m3u8"

    print("=" * 60)
    print("VERIFICA LINK PLAYLIST")
    print("=" * 60)

    # Parse playlist
    print(f"\nParsing {playlist_path}...")
    channels = parse_playlist(playlist_path)
    print(f"Trovati {len(channels)} canali")

    if not channels:
        print("Nessun canale trovato!")
        return

    # Ottieni signature
    print("\nOttenimento signature...")
    signature = get_auth_signature()
    if not signature:
        print("ERRORE: Impossibile ottenere signature!")
        return
    print("Signature ottenuta!")

    # Testa un campione (primi 20 canali)
    sample_size = min(20, len(channels))
    sample = channels[:sample_size]

    print(f"\nTest di {sample_size} canali (campione)...")
    print("-" * 60)

    results = []
    working = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(test_channel, ch, signature): ch for ch in sample}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            status_icon = "[OK]" if result["ok"] else "[FAIL]"
            status_text = f"HTTP {result['status']}" if result['status'] > 0 else result.get("error", "Errore")

            print(f"{status_icon} {result['name'][:40]:<40} {status_text}")

            if result["ok"]:
                working += 1
            else:
                failed += 1

    # Riepilogo
    print("-" * 60)
    print("\nRIEPILOGO:")
    print(f"  [OK] Funzionanti: {working}/{sample_size}")
    print(f"  [FAIL] Non funzionanti: {failed}/{sample_size}")
    print(f"  [%] Percentuale successo: {(working / sample_size) * 100:.1f}%")

    if failed > 0:
        print("\n⚠️  Alcuni canali potrebbero essere temporaneamente offline.")
        print("   I link Vavoo sono dinamici e cambiano frequentemente.")


if __name__ == "__main__":
    main()
