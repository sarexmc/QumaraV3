#!/usr/bin/env python3
"""
QUMARA - pipeline del modelo organico (OBJ de un modelador profesional) -> recursos del mod.
Uso:  python3 tools/build_model.py [ruta/carnivorous_plant.obj] [celdas=90] [textura=2048]
Entrada: carnivorous_plant.obj + albedo.jpg + emission.jpg (misma carpeta). Requiere numpy, scipy, pillow.
Salida (src/main/resources/assets/qumara/):
  model/qumara.mesh   malla decimada (~47k vertices / 32k cuads) con 4 pesos de hueso por vertice
  model/qumara.qani   esqueleto + todas las animaciones (20 fps) + trayectoria de la mano
  textures/entity/qumara.png, qumara_fury.png
"""
import sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
from mesh_tools import *
import parts
from qumara_rig import *
import anims
from animlib import write_qani

obj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'source', 'carnivorous_plant.obj')
cells = int(sys.argv[2]) if len(sys.argv) > 2 else 90
tex = int(sys.argv[3]) if len(sys.argv) > 3 else 2048
src = os.path.dirname(obj)
OUT = os.path.join(ROOT, 'src/main/resources/assets/qumara')
os.makedirs(OUT + '/model', exist_ok=True); os.makedirs(OUT + '/textures/entity', exist_ok=True)

print('1/5 leyendo OBJ...'); raw = parse_obj(obj)
alb = Image.open(os.path.join(src, 'albedo.jpg')).convert('RGB')
emi = Image.open(os.path.join(src, 'emission.jpg')).convert('RGB') if os.path.exists(os.path.join(src, 'emission.jpg')) else None
a2 = np.asarray(alb.resize((2048, 2048))) / 255.0
def sample(uv): return a2[((1 - (uv[:, 1] % 1)) * 2047).astype(int), ((uv[:, 0] % 1) * 2047).astype(int)]
print('2/5 segmentando en piezas y decimando...')
cent = raw['V'][raw['vi']].mean(1)                                          # centroide de cada triangulo
ccol = sum(sample(raw['VT'][raw['ti'][:, k]]) for k in range(3)) / 3.0
tri_label = parts.label_points(cent, ccol)
print('   triangulos por pieza:', {n: int((tri_label == i).sum()) for i, n in enumerate(parts.COMPONENTS)})
m = decimate(raw, cells, tri_label); P, UV, N, T, VL = m['P'], m['UV'], m['N'], m['T'], m['L']
print('   vertices', len(P), 'triangulos', len(T))
col = sample(UV)
print('3/5 pesos de hueso...'); import scipy.sparse as sp
_a = np.r_[T[:, 0], T[:, 1], T[:, 2], T[:, 1], T[:, 2], T[:, 0]]; _b = np.r_[T[:, 1], T[:, 2], T[:, 0], T[:, 0], T[:, 1], T[:, 2]]
_A = sp.coo_matrix((np.ones(len(_a)), (_a, _b)), shape=(len(P), len(P))).tocsr(); _A.data[:] = 1
_d = np.asarray(_A.sum(1)).ravel(); _d[_d == 0] = 1
bi, bw = parts.weights(P, col, VL, sp.diags(1 / _d) @ _A)
print('4/5 cuads y exportacion...'); quads = pair_quads(P, T)
write_qmsh(OUT + '/model/qumara.mesh', (P - ORIGIN) * S, UV, N, bi, bw, quads)
base = np.asarray(alb.resize((tex, tex), Image.LANCZOS)).astype(float) / 255.0
if emi is not None: base = np.clip(base + 0.6 * np.asarray(emi.resize((tex, tex), Image.LANCZOS)).astype(float) / 255.0, 0, 1)
Image.fromarray((base * 255).astype(np.uint8)).save(OUT + '/textures/entity/qumara.png', optimize=True)
fury = np.clip(base * np.array([1.35, 0.50, 0.45]) + np.array([0.06, 0.0, 0.0]), 0, 1)       # furia: tinte rojo
Image.fromarray((fury * 255).astype(np.uint8)).save(OUT + '/textures/entity/qumara_fury.png', optimize=True)
print('5/5 animaciones (%d)...' % len(anims.ANIMS)); write_qani(OUT + '/model/qumara.qani', anims.ANIMS)
np.savez(os.path.join(HERE, 'out', 'mesh_debug.npz'), P=P, UV=UV, T=T, idx=bi, w=bw, L=VL) if os.path.isdir(os.path.join(HERE, 'out')) else None
print('listo ->', OUT)
