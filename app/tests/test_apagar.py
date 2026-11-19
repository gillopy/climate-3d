"""Regresiones de APAGAR.bat: apagar tiene que apagar de verdad, y decirlo.

Por qué existe esta prueba: APAGAR.bat llamaba solo a `docker compose down` y
después imprimía "Listo" sin mirar el resultado. Con la app corriendo nativa
(uvicorn) no cerraba nada y aun así decía que sí.

El apagado real no se ejecuta acá a propósito: mataría la instancia que el
desarrollador tenga abierta en ese momento. Se prueban las invariantes que se
pueden leer del repo y el modo `-SoloMirar`, que es el que informa qué apagaría
sin tocar nada.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_apagar
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DESPLIEGUE = RAIZ / "despliegue"
BAT = DESPLIEGUE / "APAGAR.bat"
PS1 = DESPLIEGUE / "apagar.ps1"
PYTHON_VENV = RAIZ / ".venv" / "Scripts" / "python.exe"
POWERSHELL = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"


def _bat() -> str:
    return BAT.read_text(encoding="utf-8")


def _ps1() -> str:
    return PS1.read_text(encoding="utf-8")


def _solo_mirar() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(POWERSHELL), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PS1), "-SoloMirar"],
        cwd=str(DESPLIEGUE),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _matar(proceso: subprocess.Popen[bytes]) -> None:
    # /T se lleva a los hijos: el señuelo puede tener procesos colgando.
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proceso.pid)], capture_output=True)
    try:
        proceso.wait(timeout=10)
    except subprocess.TimeoutExpired:  # pragma: no cover - no debería pasar
        pass


class ElLanzadorDeWindows(unittest.TestCase):
    def test_el_bat_delega_en_el_script_de_apagado(self) -> None:
        # El .bat es un lanzador: la lógica vive en apagar.ps1, igual que
        # ARRANCAR.bat delega en ARRANCAR.ps1.
        self.assertIn("apagar.ps1", _bat())

    def test_el_bat_no_baja_docker_por_su_cuenta(self) -> None:
        # Sin el chequeo de `docker info` previo, el daemon apagado tira el error
        # del npipe y no baja nada. Por eso `down` no puede vivir en el .bat.
        self.assertNotIn("docker compose down", _bat())

    def test_el_bat_propaga_el_fallo(self) -> None:
        # `pause` pisa errorlevel: sin guardarlo antes, el exit 1 del .ps1 se
        # pierde y cualquier script que llame al .bat ve éxito.
        # Se miran las líneas reales: los comentarios `rem` no ejecutan nada.
        lineas = [
            linea.strip()
            for linea in _bat().splitlines()
            if linea.strip() and not linea.strip().lower().startswith("rem")
        ]
        cuerpo = "\n".join(lineas)
        self.assertIn('set "codigo=%errorlevel%"', cuerpo)
        self.assertIn("exit /b %codigo%", cuerpo)
        self.assertLess(cuerpo.index('set "codigo=%errorlevel%"'), cuerpo.index("pause"))

    def test_el_bat_va_con_crlf(self) -> None:
        # .gitattributes pide CRLF para *.bat: con LF, `goto` se porta raro.
        self.assertIn(b"\r\n", BAT.read_bytes())


class ElScriptDeApagado(unittest.TestCase):
    def test_pregunta_si_docker_responde_antes_de_bajar_el_contenedor(self) -> None:
        # El orden importa: primero `docker info`, después `compose down`.
        # Se busca el comando real (`& docker compose down`): el texto aparece
        # también en el comentario del encabezado y eso no ejecuta nada.
        texto = _ps1()
        self.assertIn("docker info", texto)
        self.assertLess(texto.index("docker info"), texto.index("& docker compose down"))

    def test_solo_mata_uvicorn_del_venv_de_este_repo(self) -> None:
        # Filtrar solo por "uvicorn" mataría el servidor de otro proyecto.
        texto = _ps1()
        self.assertIn("[regex]::Escape($venv)", texto)
        self.assertIn("$_.CommandLine -match $patronVenv", texto)

    def test_arrastra_a_los_hijos_sin_uvicorn_en_la_linea(self) -> None:
        # `uvicorn --reload` levanta el worker por multiprocessing y su linea de
        # comandos no dice "uvicorn": si no se sigue el arbol, queda vivo y el
        # puerto sigue tomado.
        texto = _ps1()
        self.assertIn("ParentProcessId", texto)

    def test_un_proceso_que_ya_no_existe_no_es_un_fallo(self) -> None:
        # Matar al padre se lleva al hijo: Stop-Process tira "no se encuentra el
        # proceso". Eso es el resultado buscado, no un error.
        texto = _ps1()
        desde = texto.index("catch {")
        bloque = texto[desde:desde + 600]
        self.assertIn("Get-Process -Id", bloque)
        self.assertIn("ya habia terminado", bloque)

    def test_solo_dice_apagado_si_de_verdad_apago_algo(self) -> None:
        # El mensaje de exito vive dentro de la rama que apago algo.
        texto = _ps1()
        rama = texto.index("if ($apagado)")
        self.assertLess(rama, texto.index("Climate 3D apagado"))

    def test_es_crlf_y_ascii_para_powershell_51(self) -> None:
        # cmd necesita CRLF (si no `goto` se porta raro) y PowerShell 5.1 lee un
        # .ps1 sin BOM como ANSI: un acento se corrompe y rompe el script.
        datos = PS1.read_bytes()
        self.assertIn(b"\r\n", datos)
        self.assertEqual([b for b in datos if b > 127], [], "apagar.ps1 tiene bytes no ASCII")
        self.assertFalse(datos.startswith(b"\xef\xbb\xbf"), "apagar.ps1 no debe tener BOM")


@unittest.skipUnless(
    os.name == "nt" and POWERSHELL.exists() and PYTHON_VENV.exists(),
    "necesita Windows, PowerShell y el .venv del repo",
)
class SoloMirarInformaLoQueApagaria(unittest.TestCase):
    def test_lista_el_proceso_sin_tocarlo(self) -> None:
        # Un python del venv con "uvicorn" en la linea de comandos: el script lo
        # detecta igual que a un servidor real, pero no abre puertos ni importa
        # la app. Así la prueba no depende de las dependencias de la web.
        senuelo = subprocess.Popen(
            [str(PYTHON_VENV), "-c", "import time; time.sleep(120)", "uvicorn"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            time.sleep(1.0)
            resultado = _solo_mirar()
            salida = resultado.stdout + resultado.stderr

            self.assertEqual(resultado.returncode, 0, salida)
            self.assertIn(f"apagaria el proceso {senuelo.pid}", salida)
            # Bug propio ya visto: listaba el proceso y abajo decía "no hay nada".
            self.assertIn("Eso es lo que apagaria", salida)
            # -SoloMirar no mata nada: el señuelo sigue vivo.
            self.assertIsNone(senuelo.poll())
        finally:
            _matar(senuelo)

    def test_lista_al_hijo_que_no_dice_uvicorn(self) -> None:
        # Reproduce `uvicorn --reload`: el padre dice "uvicorn", el worker no.
        with tempfile.TemporaryDirectory() as carpeta:
            archivo_pid = Path(carpeta) / "hijo.pid"
            codigo = (
                "import pathlib, subprocess, sys, time\n"
                "hijo = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
                "pathlib.Path(sys.argv[1]).write_text(str(hijo.pid))\n"
                "time.sleep(120)\n"
            )
            padre = subprocess.Popen(
                [str(PYTHON_VENV), "-c", codigo, str(archivo_pid), "uvicorn"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                limite = time.time() + 15
                while time.time() < limite and not archivo_pid.exists():
                    time.sleep(0.2)
                self.assertTrue(archivo_pid.exists(), "el señuelo no arrancó al hijo")
                hijo = int(archivo_pid.read_text().strip())

                resultado = _solo_mirar()
                salida = resultado.stdout + resultado.stderr

                self.assertEqual(resultado.returncode, 0, salida)
                self.assertIn(f"apagaria el proceso {padre.pid}", salida)
                self.assertIn(f"apagaria el proceso {hijo}", salida)
            finally:
                _matar(padre)

    def test_no_toca_el_uvicorn_de_otro_proyecto(self) -> None:
        # Otro venv con su propio python: si el filtro fuera solo "uvicorn",
        # apagar Climate 3D se llevaría puesto el servidor de al lado.
        with tempfile.TemporaryDirectory() as carpeta:
            otro = Path(carpeta) / "otro"
            (otro / "Scripts").mkdir(parents=True)
            shutil.copy2(PYTHON_VENV, otro / "Scripts" / "python.exe")
            config = RAIZ / ".venv" / "pyvenv.cfg"
            if config.exists():
                shutil.copy2(config, otro / "pyvenv.cfg")

            ajeno = subprocess.Popen(
                [str(otro / "Scripts" / "python.exe"), "-c", "import time; time.sleep(120)", "uvicorn"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                time.sleep(1.0)
                if ajeno.poll() is not None:
                    self.skipTest("la copia del intérprete no arranca en este entorno")

                resultado = _solo_mirar()
                salida = resultado.stdout + resultado.stderr

                self.assertEqual(resultado.returncode, 0, salida)
                self.assertNotIn(f"apagaria el proceso {ajeno.pid}", salida)
                self.assertIsNone(ajeno.poll(), "el proceso ajeno no debería morir")
            finally:
                _matar(ajeno)


if __name__ == "__main__":
    unittest.main()
