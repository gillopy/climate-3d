"""Descarga GOES-18 C04 (cirrus) para Oct 2-5 2026 UTC desde NOAA S3.

Usa el mismo bucket y formato que animacion_cirrus_g18.ipynb.
Salta archivos que ya existen localmente (>1 MB).
"""
import re, sys, urllib.request, time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

SAT, BANDA = "G18", "C04"
DATOS = Path(r"D:\Users\guill\dataset era5\goes_c04_g18")
DATOS.mkdir(parents=True, exist_ok=True)

T0 = datetime(2026, 10, 2, 0, 0)   # UTC
T1 = datetime(2026, 10, 5, 0, 0)   # UTC
PASO_MIN = 10

POR_HORA = defaultdict(list)
PATRON = re.compile(r"OR_ABI-L2-CMIPF-M6(?P<banda>C\d+)_(?P<sat>G\d+)_s(?P<s>\d{14})_")

def claves_de_la_hora(hora):
    if hora not in POR_HORA:
        pref = (f"ABI-L2-CMIPF/{hora.year}/{int(hora.strftime('%j')):03d}/"
                f"{hora.hour:02d}/")
        url = f"https://noaa-goes{SAT[1:]}.s3.amazonaws.com/?list-type=2&prefix={pref}"
        xml = urllib.request.urlopen(url, timeout=120).read().decode()
        POR_HORA[hora] = re.findall(r"<Key>([^<]+)</Key>", xml)
    return POR_HORA[hora]

def clave_de(t):
    for clave in claves_de_la_hora(t):
        m = PATRON.search(clave)
        if not m or m["banda"] != BANDA or m["sat"] != SAT:
            continue
        inicio = datetime.strptime(m["s"][:13], "%Y%j%H%M%S")
        if (inicio.hour, inicio.minute) == (t.hour, t.minute):
            return clave
    raise LookupError(f"Sin archivo {SAT} {BANDA} para {t:%Y-%m-%d %H:%M} UTC")

def ruta_local(clave):
    nombre = clave.rsplit("/", 1)[-1]
    for candidato in (Path(nombre), DATOS / nombre):
        if candidato.exists():
            return candidato
    return DATOS / nombre

def descargar(clave):
    destino = ruta_local(clave)
    if destino.exists() and destino.stat().st_size > 1_000_000:
        return destino, True  # ya existia
    url = f"https://noaa-goes{SAT[1:]}.s3.amazonaws.com/{clave}"
    with urllib.request.urlopen(url, timeout=300) as respuesta:
        with open(destino, "wb") as salida:
            while True:
                trozo = respuesta.read(1 << 20)
                if not trozo:
                    break
                salida.write(trozo)
    return destino, False

# Generar slots
slots = []
t = T0
while t < T1:
    slots.append(t)
    t += timedelta(minutes=PASO_MIN)

print(f"Total slots: {len(slots)} ({T0} -> {T1} UTC)")
print(f"Destino: {DATOS}")

descargados = 0
existentes = 0
errores = 0
inicio = time.time()

for i, t in enumerate(slots, 1):
    try:
        clave = clave_de(t)
        ruta, ya_existia = descargar(clave)
        if ya_existia:
            existentes += 1
        else:
            descargados += 1
        if i % 10 == 0 or i == len(slots):
            elapsed = time.time() - inicio
            print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC  "
                  f"descargados={descargados} existentes={existentes} errores={errores}  "
                  f"tiempo={elapsed:.0f}s", flush=True)
    except Exception as e:
        errores += 1
        print(f"[{i}/{len(slots)}] {t:%Y-%m-%d %H:%M} UTC  ERROR: {e}", flush=True)

elapsed = time.time() - inicio
print(f"\nFinalizado en {elapsed:.0f}s: descargados={descargados}, existentes={existentes}, errores={errores}")
