"""Quick shaded previews of the case pieces with matplotlib (no CAD viewer needed)."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

COLORS = ["#8fa3b8", "#b8a38f", "#9fb88f", "#b88fa8"]
LIGHT = np.array([0.3, -0.5, 0.8]) / np.linalg.norm([0.3, -0.5, 0.8])


def _mesh(part, tol=0.3):
    verts, tris = part.tessellate(tol, 0.3)
    v = np.array([[p.X, p.Y, p.Z] for p in verts])
    return v[np.array(tris)]


def render(parts: dict, path, views=((25, -60), (25, -120), (90, -90), (-35, -70)), title=""):
    tris = {n: _mesh(p) for n, p in parts.items()}
    allv = np.concatenate([t.reshape(-1, 3) for t in tris.values()])
    lo, hi = allv.min(0), allv.max(0)
    fig = plt.figure(figsize=(8 * len(views) / 2, 12), dpi=110)
    for i, (elev, azim) in enumerate(views):
        ax = fig.add_subplot(2, (len(views) + 1) // 2, i + 1, projection="3d")
        for j, (name, t) in enumerate(tris.items()):
            n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
            n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
            shade = 0.35 + 0.65 * np.clip(n @ LIGHT, 0, 1)
            base = np.array(matplotlib.colors.to_rgb(COLORS[j % len(COLORS)]))
            pc = Poly3DCollection(t, facecolors=np.clip(base * shade[:, None], 0, 1), edgecolors="none")
            ax.add_collection3d(pc)
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
        ax.set_box_aspect(hi - lo)
        ax.view_init(elev, azim)
        ax.set_axis_off()
        ax.set_title(f"elev {elev}, azim {azim}", fontsize=8)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
