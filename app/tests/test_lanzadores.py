"""Los .bat de despliegue terminan solos: nadie tiene que apretar una tecla.

Por qué existe esta prueba: después de arrancar o apagar, la ventana se quedaba
esperando (un `pause`) y había que cerrarla a mano. Ahora el éxito sale sin
esperar y el fallo espera unos segundos para que se lea el motivo, pero también
se cierra. El código de salida del .ps1 se conserva en los dos casos.

    .venv\\Scripts\\python.exe -m unittest app.tests.test_lanzadores
"""
from __future__ import annotations

import unittest
from pathlib import Path

DESPLIEGUE = Path(__file__).resolve().parents[2] / "despliegue"


def _cuerpo(nombre: str) -> str:
    """Las líneas que ejecutan algo: los comentarios `rem` no cuentan."""
    texto = (DESPLIEGUE / nombre).read_text(encoding="utf-8")
    lineas = [
        linea.strip()
        for linea in texto.splitlines()
        if linea.strip() and not linea.strip().lower().startswith("rem")
    ]
    return "\n".join(lineas)


class LosLanzadores(unittest.TestCase):
    def test_ninguno_espera_una_tecla(self) -> None:
        for nombre in ("ARRANCAR.bat", "APAGAR.bat", "ARRANCAR-DOCKER.bat"):
            with self.subTest(lanzador=nombre):
                self.assertNotIn("pause", _cuerpo(nombre))

    def test_el_exito_sale_sin_esperar(self) -> None:
        for nombre in ("ARRANCAR.bat", "APAGAR.bat"):
            with self.subTest(lanzador=nombre):
                self.assertIn('if "%codigo%"=="0" exit /b 0', _cuerpo(nombre))

    def test_el_fallo_espera_y_se_cierra_igual(self) -> None:
        for nombre in ("ARRANCAR.bat", "APAGAR.bat"):
            with self.subTest(lanzador=nombre):
                cuerpo = _cuerpo(nombre)
                # `set` tiene que ir antes: la espera deja errorlevel en cero.
                self.assertLess(
                    cuerpo.index('set "codigo=%errorlevel%"'), cuerpo.index("ping -n")
                )
                self.assertIn("exit /b %codigo%", cuerpo)

    def test_los_bat_van_con_crlf(self) -> None:
        # .gitattributes pide CRLF para *.bat: con LF, `goto` se porta raro.
        for nombre in ("ARRANCAR.bat", "APAGAR.bat", "ARRANCAR-DOCKER.bat"):
            with self.subTest(lanzador=nombre):
                self.assertIn(b"\r\n", (DESPLIEGUE / nombre).read_bytes())


class ElLanzadorDeDocker(unittest.TestCase):
    def test_compila_cuando_falta_la_imagen(self) -> None:
        # El bug: `:compilar` imprimía "se compila ahora" y seguía de largo, la
        # imagen no existía y la verificación del sello la rechazaba (fail closed).
        cuerpo = _cuerpo("ARRANCAR-DOCKER.bat")
        tramo = cuerpo[cuerpo.index(":compilar") : cuerpo.index(":imagen_ok")]
        self.assertIn("docker compose build", tramo)

    def test_el_commit_se_define_antes_del_build(self) -> None:
        # El sello se hornea con el build arg de compose: si CLIMATE3D_COMMIT se
        # define después del build, la imagen sale sin sello y se rechaza a sí misma.
        cuerpo = _cuerpo("ARRANCAR-DOCKER.bat")
        self.assertLess(
            cuerpo.index('set "CLIMATE3D_COMMIT=%COMMIT%"'),
            cuerpo.index("docker compose build"),
        )
