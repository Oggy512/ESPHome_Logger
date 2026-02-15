#!/usr/bin/env python3
import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from aioesphomeapi import APIClient, APIConnectionError, LogLevel
from zoneinfo import ZoneInfo

LOG_DIR = Path("/share/esphome_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

with open("/data/options.json") as f:
    config = json.load(f)

# Zeitzone konfigurieren
TZ_NAME = os.environ.get('TZ', 'Europe/Berlin')
try:
    LOCAL_TZ = ZoneInfo(TZ_NAME)
    print(f"Nutze Zeitzone: {TZ_NAME}")
except Exception as e:
    print(f"WARNUNG: Zeitzone {TZ_NAME} nicht gefunden, nutze UTC. Fehler: {e}")
    LOCAL_TZ = timezone.utc

# Log-Rotation Einstellungen
MAX_LOG_SIZE = 500 * 1024  # 500 KB
MAX_LOG_LINES = 2000
MAX_BACKUPS = 5

LEVEL_MAP = {
    LogLevel.LOG_LEVEL_ERROR: "ERROR",
    LogLevel.LOG_LEVEL_WARN: "WARN",
    LogLevel.LOG_LEVEL_INFO: "INFO",
    LogLevel.LOG_LEVEL_DEBUG: "DEBUG",
    LogLevel.LOG_LEVEL_VERBOSE: "VERBOSE",
    LogLevel.LOG_LEVEL_VERY_VERBOSE: "VERY_VERBOSE",
}

def strip_ansi_codes(text):
    """Entfernt ANSI-Farbcodes aus dem Text"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    
    if isinstance(text, bytes):
        text = text.decode('utf-8', errors='ignore')
    
    return ansi_escape.sub('', text)

def rotate_log(log_file):
    """Rotiert Logfiles wenn Größe oder Zeilenanzahl überschritten"""
    if not log_file.exists():
        return
    
    file_size = log_file.stat().st_size
    
    with open(log_file, 'r', encoding='utf-8') as f:
        line_count = sum(1 for _ in f)
    
    if file_size >= MAX_LOG_SIZE or line_count >= MAX_LOG_LINES:
        print(f"Rotiere {log_file.name} (Größe: {file_size} bytes, Zeilen: {line_count})")
        
        for i in range(MAX_BACKUPS - 1, 0, -1):
            old_backup = Path(f"{log_file}.{i}")
            new_backup = Path(f"{log_file}.{i + 1}")
            if old_backup.exists():
                if new_backup.exists():
                    new_backup.unlink()
                old_backup.rename(new_backup)
        
        backup_file = Path(f"{log_file}.1")
        if backup_file.exists():
            backup_file.unlink()
        log_file.rename(backup_file)
        
        print(f"Log rotiert zu {backup_file.name}")

async def log_device(device_config):
    name = device_config["name"]
    host = device_config["host"]
    password = device_config.get("password", "")
    encryption_key = device_config.get("encryption_key", "")
    
    log_file = LOG_DIR / f"{name}.log"
    line_counter = 0
    
    print(f"[{name}] Verbinde mit {host}...")
    print(f"[{name}] Logfile: {log_file}")
    
    reconnect_delay = 10
    client = None
    
    while True:
        try:
            # Erstelle neuen Client für jeden Verbindungsversuch
            if encryption_key:
                client = APIClient(host, 6053, "", noise_psk=encryption_key)
                print(f"[{name}] Nutze Encryption Key")
            elif password:
                client = APIClient(host, 6053, password)
                print(f"[{name}] Nutze API Password")
            else:
                client = APIClient(host, 6053, "")
                print(f"[{name}] Keine Authentifizierung")
            
            # Verbindung herstellen
            await client.connect(login=True)
            print(f"[{name}] Verbunden!")
            reconnect_delay = 10  # Reset bei erfolgreicher Verbindung
            
            def on_log(msg):
                nonlocal line_counter
                
                try:
                    now = datetime.now(LOCAL_TZ)
                    timestamp = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    level = LEVEL_MAP.get(msg.level, "UNKNOWN")
                    
                    message = strip_ansi_codes(msg.message)
                    
                    log_line = f"[{timestamp}] [{level:13s}] {message}\n"
                    
                    if line_counter % 100 == 0 and line_counter > 0:
                        rotate_log(log_file)
                    
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(log_line)
                    
                    line_counter += 1
                    
                except Exception as e:
                    print(f"[{name}] FEHLER beim Schreiben: {e}")
            
            # Logs abonnieren
            try:
                await client.subscribe_logs(on_log, log_level=LogLevel.LOG_LEVEL_VERBOSE)
            except TypeError as e:
                print(f"[{name}] subscribe_logs TypeError: {e}")
                result = client.subscribe_logs(on_log, log_level=LogLevel.LOG_LEVEL_VERBOSE)
                if asyncio.iscoroutine(result):
                    await result
            
            # Startup-Log
            try:
                now = datetime.now(LOCAL_TZ)
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"# Logger gestartet um {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
                print(f"[{name}] Schreibzugriff auf {log_file} OK")
                print(f"[{name}] Aktuelle lokale Zeit: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                print(f"[{name}] FEHLER: Kann nicht in {log_file} schreiben: {e}")
            
            # Verbindung halten
            while True:
                await asyncio.sleep(1)
                
        except APIConnectionError as e:
            error_msg = str(e)
            
            if "Already connected" in error_msg:
                print(f"[{name}] Verbindung besteht bereits, warte länger vor erneutem Versuch...")
                reconnect_delay = 30  # Längere Wartezeit bei "Already connected"
            else:
                print(f"[{name}] Verbindungsfehler: {e}")
            
            print(f"[{name}] Versuche Reconnect in {reconnect_delay} Sekunden...")
            
            # Cleanup der alten Verbindung
            if client:
                try:
                    await client.disconnect()
                    await asyncio.sleep(2)  # Warte etwas nach Disconnect
                except:
                    pass
                client = None
            
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 1.2, 60)  # Langsamer Backoff
            
        except TypeError as e:
            if "functools.partial" in str(e):
                print(f"[{name}] API-Kompatibilitätsproblem: {e}")
                print(f"[{name}] Versuche Reconnect in {reconnect_delay} Sekunden...")
                
                if client:
                    try:
                        await client.disconnect()
                        await asyncio.sleep(2)
                    except:
                        pass
                    client = None
                
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, 60)
            else:
                raise
                
        except Exception as e:
            print(f"[{name}] Unerwarteter Fehler: {e}")
            print(f"[{name}] Typ: {type(e).__name__}")
            import traceback
            print(f"[{name}] Traceback:\n{traceback.format_exc()}")
            print(f"[{name}] Versuche Reconnect in {reconnect_delay} Sekunden...")
            
            if client:
                try:
                    await client.disconnect()
                    await asyncio.sleep(2)
                except:
                    pass
                client = None
            
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 1.5, 60)

async def main():
    devices = config.get("devices", [])
    
    if not devices:
        print("FEHLER: Keine Geräte konfiguriert!")
        return
    
    print(f"Starte Logger für {len(devices)} Gerät(e)...")
    print(f"Log-Verzeichnis: {LOG_DIR}")
    print(f"Log-Rotation: max {MAX_LOG_LINES} Zeilen ODER {MAX_LOG_SIZE} bytes")
    print(f"Backup-Anzahl: {MAX_BACKUPS}")
    
    if not Path("/share").exists():
        print("WARNUNG: /share Verzeichnis nicht gefunden!")
        print("Stelle sicher dass 'map: [\"share:rw\"]' in config.yaml vorhanden ist!")
    
    tasks = [log_device(device) for device in devices]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
