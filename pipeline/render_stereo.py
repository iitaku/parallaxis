"""Step 3 — Stereo pair rendering from a trained 3DGS scene.

Renders left-eye and right-eye images from an arbitrary viewpoint using the
gsplat rasterisation API.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from .config import PipelineConfig

if TYPE_CHECKING:
    import torch

log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Camera utilities
# ------------------------------------------------------------------

def look_at_matrix(
    position: np.ndarray,
    target: np.ndarray,
    up: np.ndarray,
) -> np.ndarray:
    """Build a 4×4 camera-to-world matrix (OpenGL convention: -Z forward)."""
    forward = target - position
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, up)
    right = right / np.linalg.norm(right)
    actual_up = np.cross(right, forward)

    c2w = np.eye(4, dtype=np.float64)
    c2w[:3, 0] = right
    c2w[:3, 1] = actual_up
    c2w[:3, 2] = -forward  # OpenGL: camera looks along -Z
    c2w[:3, 3] = position
    return c2w


def make_stereo_cameras(
    position: np.ndarray,
    target: np.ndarray,
    up: np.ndarray,
    ipd: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (w2c_left, w2c_right) as 4×4 arrays."""
    c2w = look_at_matrix(position, target, up)
    right = c2w[:3, 0]

    c2w_left = c2w.copy()
    c2w_left[:3, 3] -= right * (ipd / 2)

    c2w_right = c2w.copy()
    c2w_right[:3, 3] += right * (ipd / 2)

    w2c_left = np.linalg.inv(c2w_left)
    w2c_right = np.linalg.inv(c2w_right)
    return w2c_left, w2c_right


# ------------------------------------------------------------------
# Checkpoint loading
# ------------------------------------------------------------------

def load_gsplat_checkpoint(path: Path, device: str = "cuda") -> dict:
    """Load a gsplat checkpoint and return Gaussian parameters."""
    import torch

    ckpt = torch.load(path, map_location=device, weights_only=False)

    means = ckpt["means"]
    quats = ckpt["quats"]
    scales = ckpt["scales"]
    opacities = ckpt["opacities"]
    sh0 = ckpt["sh0"]
    shN = ckpt["shN"]

    colors = torch.cat([sh0, shN], dim=1)
    sh_degree = int(math.sqrt(colors.shape[1]) - 1)

    log.info(
        "Loaded %d Gaussians (SH degree %d) from %s",
        means.shape[0], sh_degree, path,
    )
    return {
        "means": means,
        "quats": quats,
        "scales": scales,
        "opacities": opacities,
        "colors": colors,
        "sh_degree": sh_degree,
    }


# ------------------------------------------------------------------
# Rendering
# ------------------------------------------------------------------

def render_stereo(cfg: PipelineConfig) -> tuple[Path, Path]:
    """Render a stereo pair and return (left_path, right_path)."""
    import torch
    from gsplat import rasterization
    from PIL import Image

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        log.warning("CUDA not available — rendering on CPU (very slow)")

    # Load checkpoint
    ckpt_path = cfg.checkpoint_path
    if not ckpt_path.exists():
        # Try to find any checkpoint
        model_dir = Path(cfg.model_dir)
        candidates = sorted(model_dir.glob("ckpt_*.pt"), reverse=True)
        if not candidates:
            raise FileNotFoundError(f"No checkpoint found in {model_dir}")
        ckpt_path = candidates[0]
        log.info("Using checkpoint: %s", ckpt_path)

    gs = load_gsplat_checkpoint(ckpt_path, device)

    # Build stereo view matrices
    position = np.array(cfg.camera_position, dtype=np.float64)
    target = np.array(cfg.camera_look_at, dtype=np.float64)
    up = np.array(cfg.camera_up, dtype=np.float64)

    w2c_left, w2c_right = make_stereo_cameras(position, target, up, cfg.ipd)
    viewmats = torch.tensor(
        np.stack([w2c_left, w2c_right]),
        dtype=torch.float32,
        device=device,
    )

    # Camera intrinsics (same for both eyes)
    cx = cfg.render_width / 2.0
    cy = cfg.render_height / 2.0
    K = torch.tensor(
        [[cfg.fx, 0.0, cx], [0.0, cfg.fy, cy], [0.0, 0.0, 1.0]],
        dtype=torch.float32,
        device=device,
    )
    Ks = K.unsqueeze(0).expand(2, -1, -1)

    log.info(
        "Rendering stereo: %dx%d, HFOV=%.1f°, IPD=%.0fmm",
        cfg.render_width, cfg.render_height, cfg.hfov, cfg.cdist,
    )

    # Render
    with torch.no_grad():
        rendered, alphas, meta = rasterization(
            gs["means"],
            gs["quats"],
            gs["scales"],
            gs["opacities"],
            gs["colors"],
            viewmats,
            Ks,
            cfg.render_width,
            cfg.render_height,
            sh_degree=gs["sh_degree"],
        )

    # Save
    output_dir = Path(cfg.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for i, name in enumerate(["left", "right"]):
        img = rendered[i].clamp(0, 1).cpu().numpy()
        img_uint8 = (img * 255).astype(np.uint8)
        out_path = output_dir / f"{name}.png"
        Image.fromarray(img_uint8).save(out_path)
        log.info("Saved %s", out_path)
        paths.append(out_path)

    return paths[0], paths[1]


# ------------------------------------------------------------------
# Camera path rendering (for spatial video)
# ------------------------------------------------------------------

def render_camera_path(
    cfg: PipelineConfig,
    positions: list[list[float]],
    targets: list[list[float]],
) -> Path:
    """Render a sequence of stereo frames along a camera path.

    Returns the directory containing left_NNNN.png / right_NNNN.png frames.
    """
    import torch
    from gsplat import rasterization
    from PIL import Image

    device = "cuda" if torch.cuda.is_available() else "cpu"

    ckpt_path = cfg.checkpoint_path
    if not ckpt_path.exists():
        candidates = sorted(Path(cfg.model_dir).glob("ckpt_*.pt"), reverse=True)
        if not candidates:
            raise FileNotFoundError(f"No checkpoint found in {cfg.model_dir}")
        ckpt_path = candidates[0]

    gs = load_gsplat_checkpoint(ckpt_path, device)

    frames_dir = Path(cfg.output_dir) / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    up = np.array(cfg.camera_up, dtype=np.float64)
    cx = cfg.render_width / 2.0
    cy = cfg.render_height / 2.0
    K = torch.tensor(
        [[cfg.fx, 0.0, cx], [0.0, cfg.fy, cy], [0.0, 0.0, 1.0]],
        dtype=torch.float32,
        device=device,
    )
    Ks = K.unsqueeze(0).expand(2, -1, -1)

    n_frames = len(positions)
    log.info("Rendering %d stereo frames along camera path", n_frames)

    for idx in range(n_frames):
        pos = np.array(positions[idx], dtype=np.float64)
        tgt = np.array(targets[idx], dtype=np.float64)
        w2c_left, w2c_right = make_stereo_cameras(pos, tgt, up, cfg.ipd)
        viewmats = torch.tensor(
            np.stack([w2c_left, w2c_right]),
            dtype=torch.float32,
            device=device,
        )

        with torch.no_grad():
            rendered, _, _ = rasterization(
                gs["means"], gs["quats"], gs["scales"],
                gs["opacities"], gs["colors"],
                viewmats, Ks, cfg.render_width, cfg.render_height,
                sh_degree=gs["sh_degree"],
            )

        for i, name in enumerate(["left", "right"]):
            img = rendered[i].clamp(0, 1).cpu().numpy()
            img_uint8 = (img * 255).astype(np.uint8)
            out_path = frames_dir / f"{name}_{idx:04d}.png"
            Image.fromarray(img_uint8).save(out_path)

        if (idx + 1) % 10 == 0 or idx == n_frames - 1:
            log.info("  rendered %d/%d frames", idx + 1, n_frames)

    return frames_dir
