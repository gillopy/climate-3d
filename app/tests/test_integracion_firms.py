"""Contrato entre la receta y los renderers de FIRMS.

Esto es el hueco del item 6: la lógica de los focos estaba probada por partes, pero
nada verificaba que la receta y cada script **se pusieran de acuerdo**. Un flag que
la receta manda y el renderer no declara no lo detecta ningún test unitario: el job
muere en runtime con "unrecognized arguments".

Se verifica, para cada producto que dibuja focos:
  * que el plan tenga el paso de FIRMS, antes del render;
  * que la carpeta que baja sea la misma que el render lee;
  * que **cada** bandera `--firms*` del render exista en ese script (AST del
    `add_argument`) y que su valor esté dentro de `choices`;
  * que ningún renderer quede "a medias" (con `--firms` y sin sus compañeras).

    app\\.venv\\Scripts\\python.exe -m unittest discover -s app\\tests
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.api import catalog, recipes  # noqa: E402

#: Producto -> script que dibuja los focos.
RENDERERS = {
    "snapshot_paraguay": "cuadros/snapshot_paraguay.py",
    "geocolor": "cuadros/cuadros_geocolor.py",
    "goes_firetemp": "prototipos/poster_goes_rgb.py",
    "goes_truecolor": "prototipos/poster_goes_truecolor.py",
}

COMPANERAS = ("--firms-ventana", "--firms-alcance", "--firms-entrada")


def declaradas(script: str) -> dict[str, dict]:
    """`{bandera: {"choices": [...], "ref": "VENTANAS"}}` del script.

    Se lee el AST y no se ejecuta el módulo: los prototipos importan matplotlib y
    xarray, que el `.venv` de la API no tiene. Si `choices` es una referencia a una
    constante (`VENTANAS` o `tc.VENTANAS`) se guarda el nombre en `ref`.
    """
    arbol = ast.parse((RAIZ / script).read_text(encoding="utf-8"))
    banderas: dict[str, dict] = {}
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        funcion = nodo.func
        if not (isinstance(funcion, ast.Attribute) and funcion.attr == "add_argument"):
            continue
        if not nodo.args or not isinstance(nodo.args[0], ast.Constant):
            continue
        nombre = nodo.args[0].value
        if not isinstance(nombre, str) or not nombre.startswith("--"):
            continue
        opciones, referencia = None, None
        for clave in nodo.keywords:
            if clave.arg != "choices":
                continue
            if isinstance(clave.value, (ast.Tuple, ast.List)):
                opciones = [elemento.value for elemento in clave.value.elts
                            if isinstance(elemento, ast.Constant)]
            elif isinstance(clave.value, ast.Name):
                referencia = clave.value.id
            elif isinstance(clave.value, ast.Attribute):
                referencia = clave.value.attr
        banderas[nombre] = {"choices": opciones, "ref": referencia}
    return banderas


class ContratoRecetaRenderer(unittest.TestCase):
    """Lo que la receta manda es lo que el script acepta."""

    def _plan(self, producto: str, **extra):
        params = {s.name: s.default for s in catalog.get_product(producto).params}
        params.update({"firms": True, "animar": False, "snapshot": True,
                       "ventana": {"start": "2026-11-05", "end": "2026-11-05"},
                       "hora": 15, "minuto": "00"})
        params.update(extra)
        return recipes.planear(producto, params, Path("C:/tmp/work"))

    def test_cada_producto_planifica_y_dibuja(self):
        for producto, script in RENDERERS.items():
            with self.subTest(producto=producto):
                plan = self._plan(producto)
                pasos = [paso.script for paso in plan.pasos]
                self.assertIn("descargar/firms.py", pasos)
                self.assertIn(script, pasos)
                self.assertLess(pasos.index("descargar/firms.py"),
                                pasos.index(script),
                                "los focos se bajan después de usarlos")

    def test_la_carpeta_que_baja_es_la_que_lee(self):
        for producto, script in RENDERERS.items():
            with self.subTest(producto=producto):
                plan = self._plan(producto)
                descarga = next(p for p in plan.pasos
                                if p.script == "descargar/firms.py")
                render = next(p for p in plan.pasos if p.script == script)
                salida = descarga.args[descarga.args.index("--out") + 1]
                entrada = render.args[render.args.index("--firms-entrada") + 1]
                self.assertEqual(salida, entrada)

    def test_cada_bandera_existe_y_su_valor_es_valido(self):
        for producto, script in RENDERERS.items():
            with self.subTest(producto=producto):
                plan = self._plan(producto, firms_ventana="48h",
                                  firms_alcance="paraguay")
                render = next(p for p in plan.pasos if p.script == script)
                conocidas = declaradas(script)
                args = render.args
                for indice, token in enumerate(args):
                    if token == "--firms":
                        self.assertIn("--firms", conocidas, script)
                        continue
                    if not token.startswith("--firms-"):
                        continue
                    self.assertIn(token, conocidas,
                                  f"{script} no declara {token}")
                    valor = args[indice + 1]
                    opciones = conocidas[token]["choices"]
                    if opciones is not None:
                        self.assertIn(valor, opciones,
                                      f"{script}: {token} {valor!r} fuera de "
                                      f"{opciones}")

    def test_la_ventana_del_render_es_la_de_la_descarga(self):
        from firms import VENTANAS

        for producto, script in RENDERERS.items():
            with self.subTest(producto=producto):
                plan = self._plan(producto, firms_ventana="6h")
                render = next(p for p in plan.pasos if p.script == script)
                ventana = render.args[render.args.index("--firms-ventana") + 1]
                self.assertIn(ventana, VENTANAS)
                # El snapshot resuelve el instante con --ultima y pide por --ventana;
                # los demás piden un rango --desde/--hasta. Si la descarga declara la
                # ventana, tiene que coincidir con la del render.
                descarga = next(p for p in plan.pasos
                                if p.script == "descargar/firms.py")
                if "--ventana" in descarga.args:
                    self.assertEqual(
                        descarga.args[descarga.args.index("--ventana") + 1], ventana)


class NingunRendererAMedias(unittest.TestCase):
    """Un renderer que dibuja focos declara el juego completo de banderas."""

    def test_los_que_tienen_firms_tienen_sus_companeras(self):
        for script in RENDERERS.values():
            with self.subTest(script=script):
                banderas = declaradas(script)
                self.assertIn("--firms", banderas)
                for companera in COMPANERAS:
                    self.assertIn(companera, banderas, script)

    def test_la_ventana_ofrecida_es_la_que_el_descargador_entiende(self):
        from firms import VENTANAS

        for script in RENDERERS.values():
            with self.subTest(script=script):
                spec = declaradas(script)["--firms-ventana"]
                if spec["choices"] is not None:
                    self.assertEqual(spec["choices"], list(VENTANAS), script)
                else:
                    # `choices=VENTANAS` (constante compartida) en vez de literales.
                    self.assertTrue(str(spec["ref"]).endswith("VENTANAS"), script)


class DiscoNativo(unittest.TestCase):
    """El disco nativo también dibuja focos: antes los ignoraba en silencio."""

    def _plan(self):
        params = {s.name: s.default
                  for s in catalog.get_product("goes_truecolor").params}
        params.update({"firms": True, "animar": False, "snapshot": True,
                       "encuadre": "disco", "paraguay": False,
                       "ventana": {"start": "2026-11-05", "end": "2026-11-05"},
                       "hora": 15, "minuto": "00"})
        return recipes.planear("goes_truecolor", params, Path("C:/tmp/work"))

    def test_baja_los_focos_y_los_pasa_al_render(self):
        plan = self._plan()
        pasos = [paso.script for paso in plan.pasos]
        self.assertIn("descargar/firms.py", pasos)
        disco = next(p for p in plan.pasos
                     if p.script == "prototipos/poster_goes_disco.py")
        for bandera in ("--firms", "--firms-ventana", "--firms-alcance",
                        "--firms-entrada"):
            self.assertIn(bandera, disco.args)

    def test_el_disco_declara_las_banderas(self):
        conocidas = declaradas("prototipos/poster_goes_disco.py")
        for bandera in ("--firms", *COMPANERAS):
            self.assertIn(bandera, conocidas)


class RenderersDeFocos(unittest.TestCase):
    """La lista de renderers del contrato cubre todo script que dibuje focos."""

    def test_todo_script_con_firms_esta_en_el_contrato(self):
        for archivo in sorted((RAIZ / "prototipos").glob("*.py")):
            if "--firms" in archivo.read_text(encoding="utf-8"):
                self.assertIn(f"prototipos/{archivo.name}",
                              set(RENDERERS.values()) | {"prototipos/poster_goes_disco.py"},
                              archivo.name)


class ApagadoNoDejaRastro(unittest.TestCase):
    """Con el toggle apagado, ni paso ni banderas, en los cuatro productos."""

    def test_sin_firms_no_hay_rastro(self):
        for producto, script in RENDERERS.items():
            with self.subTest(producto=producto):
                params = {s.name: s.default
                          for s in catalog.get_product(producto).params}
                params.update({"firms": False, "animar": False, "snapshot": True,
                               "ventana": {"start": "2026-11-05",
                                           "end": "2026-11-05"},
                               "hora": 15, "minuto": "00"})
                plan = recipes.planear(producto, params, Path("C:/tmp/work"))
                scripts = [paso.script for paso in plan.pasos]
                self.assertNotIn("descargar/firms.py", scripts)
                render = next(p for p in plan.pasos if p.script == script)
                self.assertFalse([token for token in render.args
                                  if token.startswith("--firms")], producto)


if __name__ == "__main__":
    unittest.main()
