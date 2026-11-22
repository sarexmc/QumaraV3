"""Segmentacion del modelo en PIEZAS independientes (por triangulo) y pesos de hueso por pieza.
Idea clave: antes de decimar se etiqueta cada triangulo con su pieza; la decimacion nunca fusiona vertices de piezas distintas
(asi no hay triangulos 'puente' entre, p.ej., lengua y mandibula que se estiren al animar). Cada pieza rigida va 100 % a su hueso;
las cadenas articuladas (cuerpo+brazo, lengua, flor) usan pesos continuos a lo largo del hueso."""
import numpy as np
from qumara_rig import *

COMPONENTS = ['body', 'head', 'jaw', 'tongue', 'petalo_sup', 'petalo_izq', 'petalo_der', 'petalo_fizq', 'petalo_fder', 'hoja_1', 'hoja_2', 'flor']
CID = {n: i for i, n in enumerate(COMPONENTS)}

def seg_dist(P, a, b):
    ab = b - a; t = np.clip(((P - a) @ ab) / (ab @ ab + 1e-12), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1), t

def smoothstep(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)

def color_classes(c):
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    pink = (r > 0.45) & (g < 0.45) & (b > 0.22) & (r > g * 1.6)
    purple = (b > r * 0.8) & (b > g * 1.3) & (b > 0.22)
    olive = (g > b * 1.25) & (g > 0.2) & (r > 0.15) & (g > r * 0.75)
    mag = (r > 0.5) & (g < 0.28) & (b > 0.35)
    return pink, purple, olive, mag

def arm_mask(P, pink):
    X, Y, Z = P[:, 0], P[:, 1], P[:, 2]
    a = (X < -0.28) & (Y > -0.62) & ((Z > 0.40) | ((Y < -0.08) & (Z > 0.08)) | ((Y < 0.10) & (Z > 0.30) & ~pink))
    a |= (X < -0.62) & (Y > -0.62) & (Z > 0.22)
    return a

def tongue_dist(P):
    pts = [np.array(BONES[f'lengua_{i}'][1]) for i in range(1, NT + 1)] + [np.array(BONES[f'lengua_{NT}'][2])]
    d = np.full(len(P), 9.0)
    for a, b in zip(pts[:-1], pts[1:]): d = np.minimum(d, seg_dist(P, a, b)[0])
    return d

def label_points(P, c):
    """Pieza de cada punto (centroide de triangulo + color medio). Devuelve array de ids de COMPONENTS."""
    X, Y, Z = P[:, 0], P[:, 1], P[:, 2]
    pink, purple, olive, mag = color_classes(c)
    L = np.full(len(P), CID['body'], np.int8)
    head = (np.abs(X) < 0.34) & (Z > -0.16) & (Y > -0.42) & (Y < 0.50) & ~olive
    L[head] = CID['head']
    L[head & (Y < -0.02) & (Z > 0.20) & (np.abs(X) < 0.26)] = CID['jaw']
    L[(X < -0.18) & (Y > 0.08) & (Z < 0.38)] = CID['petalo_izq']
    L[(X > 0.18) & (Y > 0.08) & (Z < 0.38)] = CID['petalo_der']
    sup = (np.abs(X) < 0.34) & (Y > 0.30) & (Z < 0.10)
    L[sup & (~head | ((Z < 0.0) & (Y > 0.36)))] = CID['petalo_sup']
    L[pink & (X > -0.68) & (X < -0.2) & (Z > 0.05) & (Z < 0.38) & (Y > -0.25) & (Y < 0.12)] = CID['petalo_fizq']
    L[pink & (X > 0.2) & (X < 0.70) & (Z > 0.0) & (Z < 0.40) & (Y > -0.30) & (Y < 0.12)] = CID['petalo_fder']
    L[olive & (X > 0.38) & (Y > 0.10)] = CID['hoja_1']
    L[olive & (X > 0.38) & (Y <= 0.10) & (Y > -0.55)] = CID['hoja_2']
    flor = ((Y > 0.55) & (X > 0.12) & (X < 0.75) & ~purple) | ((Y > 0.80) & (X > -0.2) & (X < 0.30) & (Z < 0.0) & ~purple)
    L[flor] = CID['flor']
    L[arm_mask(P, pink)] = CID['body']                                 # el brazo manda sobre petalos/hojas que lo rozan
    L[(mag & (tongue_dist(P) < 0.07) & (Z > 0.10) & (Y < 0.06))] = CID['tongue']
    return L

def weights(P, c, L, adj=None, iters=10):
    """P (n,3) mesh, c (n,3) color, L (n,) componente por vertice -> (idx uint8 (n,4), w float32 (n,4))."""
    n = len(P); W = np.zeros((n, len(NAMES))); X, Y, Z = P[:, 0], P[:, 1], P[:, 2]
    pink = color_classes(c)[0]
    for name in COMPONENTS:
        m = np.where(L == CID[name])[0]
        if len(m) == 0: continue
        Pm = P[m]
        if name == 'body':
            armv = arm_mask(Pm, pink[m]); rad = np.hypot(Pm[:, 0], Pm[:, 2] - 0.05); roots = (Pm[:, 1] < -0.80) & (rad > 0.22) & ~armv
            # tronco -> cuello a lo largo de y
            t = smoothstep((Pm[:, 1] + 0.72) / 0.5)
            w = np.zeros((len(m), len(NAMES))); w[:, IDX['tronco']] = 1 - t; w[:, IDX['cuello']] = t
            tb = smoothstep((Pm[:, 1] + 0.97) / 0.30)          # el pie del tronco sigue a la raiz; sube a 'tronco' gradualmente
            w[:, IDX['raiz']] = (1 - tb) * (1 - 0.0); w[:, IDX['tronco']] = tb * (1 - t); w[:, IDX['cuello']] = tb * t + 0.0
            w[:, IDX['cuello']] *= 1.0
            # raices: 4 huesos segun direccion, mezcla radial con la raiz
            names = np.where(np.abs(Pm[:, 0]) > np.abs(Pm[:, 2] - 0.05), np.where(Pm[:, 0] < 0, 'raices_o', 'raices_e'), np.where(Pm[:, 2] - 0.05 < 0, 'raices_n', 'raices_s'))
            k = smoothstep((rad - 0.22) / 0.4)
            for i in np.where(roots)[0]:
                w[i] = 0; w[i, IDX[names[i]]] = k[i]; w[i, IDX['raiz']] = 1 - k[i]
            # brazo: pesos continuos por distancia a los segmentos (hombro, antebrazo, mano, dedos)
            ai = np.where(armv)[0]
            if len(ai):
                cand = ['cuello', 'brazo', 'antebrazo', 'mano', 'dedo_1', 'dedo_2', 'pulgar']
                D = np.zeros((len(ai), len(cand))); Pa = Pm[ai]; sh = np.array(BONES['brazo'][1])
                for kk, nm in enumerate(cand):
                    a = np.array(BONES[nm][1]); b2 = np.array(BONES[nm][2])
                    if nm == 'cuello': a, b2 = sh + np.array([0.28, 0.05, -0.05]), sh + np.array([0.35, 0.10, -0.05])
                    d, _ = seg_dist(Pa, a, b2); D[:, kk] = d / max(BONES[nm][3], 0.06)
                hand = (Pa[:, 2] > 0.46) & (Pa[:, 1] > -0.10); pk = pink[m][ai]
                D[~(hand & pk), 4:] += 6.0; D[~hand, 3] += 1.5
                E = np.exp(-(D ** 2) * 0.55); E /= E.sum(1, keepdims=True) + 1e-9
                w[ai] = 0
                for kk, nm in enumerate(cand): w[ai, IDX[nm]] = E[:, kk]
            W[m] = w
        elif name == 'tongue':
            # pesos continuos: proyeccion sobre la polilinea -> dos huesos vecinos (funcion sombrero), sin saltos
            pts = [np.array(BONES[f'lengua_{i}'][1]) for i in range(1, NT + 1)] + [np.array(BONES[f'lengua_{NT}'][2])]
            best = np.full(len(m), 9.0); s = np.zeros(len(m))
            for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
                d, t = seg_dist(Pm, a, b); upd = d < best; best[upd] = d[upd]; s[upd] = i + t[upd]
            node = np.clip(s, 0, NT - 1e-6); j0 = np.floor(node).astype(int); f = smoothstep(node - j0)
            for i in range(len(m)):
                W[m[i], IDX[f'lengua_{j0[i] + 1}']] += 1.0 - f[i]
                W[m[i], IDX[f'lengua_{min(j0[i] + 2, NT)}']] += f[i]
        elif name == 'flor':
            t = smoothstep((Pm[:, 1] - 0.62) / 0.2)
            W[m, IDX['flor_1']] = 1 - t; W[m, IDX['flor_2']] = t
        else:
            W[m, IDX[{'head': 'cabeza', 'jaw': 'mandibula'}.get(name, name)]] = 1.0
    if adj is not None:                                                   # difusion por la malla (solo cuerpo/brazo; las piezas estan separadas, no hay fugas)
        bm = (L == CID['body'])
        for _ in range(iters):
            Wn = adj @ W
            W[bm] = 0.5 * W[bm] + 0.5 * Wn[bm]
    idx = np.argsort(-W, axis=1)[:, :4]; w4 = np.take_along_axis(W, idx, 1); w4 /= (w4.sum(1, keepdims=True) + 1e-12)
    return idx.astype(np.uint8), w4.astype(np.float32)
