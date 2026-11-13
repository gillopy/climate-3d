"""Métricas y muestreo para validar productos NISAR contra una referencia.

Funciones puras (numpy) para que la validación sea reproducible y testeable:
matriz de confusión, precisión/recall/F1/IoU, bootstrap y muestreo estratificado
con adelgazamiento espacial.
"""
from __future__ import annotations

import numpy as np


def matriz_confusion(
    referencia: np.ndarray, prediccion: np.ndarray
) -> tuple[int, int, int, int]:
    ref = np.asarray(referencia, dtype=bool)
    pred = np.asarray(prediccion, dtype=bool)
    if ref.shape != pred.shape:
        raise ValueError("referencia y prediccion deben tener la misma forma")
    tp = int(np.sum(ref & pred))
    fp = int(np.sum(~ref & pred))
    fn = int(np.sum(ref & ~pred))
    tn = int(np.sum(~ref & ~pred))
    return tp, fp, fn, tn


def metricas(tp: int, fp: int, fn: int, tn: int) -> dict[str, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    iou = tp / (tp + fp + fn) if tp + fp + fn else 0.0
    total = tp + fp + fn + tn
    accuracy = (tp + tn) / total if total else 0.0
    return {
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "tn": float(tn),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "iou": iou,
        "accuracy": accuracy,
    }


def metricas_ponderadas(
    tp: int,
    fp: int,
    fn: int,
    tn: int,
    peso_positivo: float,
    peso_negativo: float,
) -> dict[str, float]:
    """Reexpande una muestra estratificada a la prevalencia real.

    La muestra balanceada (mitad pérdida, mitad estable) no sirve para precisión
    operativa; con los pesos de clase sí se aproxima al mapa completo.
    """
    return metricas(
        tp * peso_positivo,
        fp * peso_negativo,
        fn * peso_positivo,
        tn * peso_negativo,
    )


def bootstrap_ic(
    referencia: np.ndarray,
    prediccion: np.ndarray,
    n: int = 500,
    seed: int = 42,
) -> dict[str, dict[str, float]]:
    """IC bootstrap al 95 % remuestreando píxeles.

    Ojo: no corrige autocorrelación espacial; el muestreo ya adelgaza los puntos.
    """
    ref = np.asarray(referencia, dtype=bool).ravel()
    pred = np.asarray(prediccion, dtype=bool).ravel()
    if ref.size != pred.size:
        raise ValueError("referencia y prediccion deben tener el mismo tamaño")
    generador = np.random.default_rng(seed)
    valores: dict[str, list[float]] = {"precision": [], "recall": [], "f1": []}
    for _ in range(max(1, int(n))):
        indices = generador.integers(0, ref.size, ref.size)
        fila = metricas(*matriz_confusion(ref[indices], pred[indices]))
        for clave in valores:
            valores[clave].append(fila[clave])
    return {
        clave: {
            "mean": float(np.mean(valores[clave])),
            "p2_5": float(np.percentile(valores[clave], 2.5)),
            "p97_5": float(np.percentile(valores[clave], 97.5)),
        }
        for clave in valores
    }


def muestreo_estratificado(
    mascaras: dict[str, np.ndarray],
    n_por_clase: int,
    seed: int = 42,
    separacion: int = 2,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Muestrea filas/columnas por clase, adelgazando la grilla.

    `separacion=2` toma uno de cada 2x2 para reducir autocorrelación espacial.
    """
    generador = np.random.default_rng(seed)
    salida: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    paso = max(1, int(separacion))
    for nombre, mascara in mascaras.items():
        filas, columnas = np.nonzero(np.asarray(mascara, dtype=bool))
        if paso > 1 and filas.size:
            quedan = (filas % paso == 0) & (columnas % paso == 0)
            filas, columnas = filas[quedan], columnas[quedan]
        if filas.size == 0:
            salida[nombre] = (filas, columnas)
        elif filas.size <= n_por_clase:
            salida[nombre] = (filas, columnas)
        else:
            indices = generador.choice(filas.size, int(n_por_clase), replace=False)
            salida[nombre] = (filas[indices], columnas[indices])
    return salida
