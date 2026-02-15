"""Step 2 — 3D Gaussian Splatting training.

Trains a 3DGS model from COLMAP output and exports a checkpoint + PLY file.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from .config import PipelineConfig

log = logging.getLogger(__name__)


def train(cfg: PipelineConfig) -> Path:
    """Train a 3DGS scene and return the path to the checkpoint.

    Backends:

    * ``gsplat``    — uses gsplat's ``simple_trainer.py`` (NVIDIA CUDA)
    * ``opensplat`` — uses OpenSplat CLI (Apple Metal / CUDA / CPU)
    """
    if cfg.training_backend == "gsplat":
        return _train_gsplat(cfg)
    elif cfg.training_backend == "opensplat":
        return _train_opensplat(cfg)
    else:
        raise ValueError(f"Unknown training backend: {cfg.training_backend!r}")


# ------------------------------------------------------------------
# gsplat backend
# ------------------------------------------------------------------

def _find_gsplat_trainer() -> Path:
    """Locate gsplat's simple_trainer.py."""
    # Try the installed package location
    try:
        import gsplat
        pkg_dir = Path(gsplat.__file__).resolve().parent.parent
        candidates = [
            pkg_dir / "examples" / "simple_trainer.py",
            pkg_dir / "simple_trainer.py",
        ]
        for c in candidates:
            if c.exists():
                return c
    except ImportError:
        pass

    # Try common install locations
    for base in [Path.home() / "gsplat", Path("/opt/gsplat"), Path(".")]:
        p = base / "examples" / "simple_trainer.py"
        if p.exists():
            return p

    raise RuntimeError(
        "Could not find gsplat's simple_trainer.py.  "
        "Install gsplat: pip install gsplat  "
        "and ensure the examples/ directory is accessible, "
        "or clone https://github.com/nerfstudio-project/gsplat"
    )


def _train_gsplat(cfg: PipelineConfig) -> Path:
    """Train with gsplat's simple_trainer."""
    colmap_dir = Path(cfg.colmap_dir)
    model_dir = Path(cfg.model_dir)

    ckpt = cfg.checkpoint_path
    if ckpt.exists():
        log.info("Checkpoint already exists at %s — skipping training", ckpt)
        return ckpt

    model_dir.mkdir(parents=True, exist_ok=True)

    # The COLMAP data directory expected by gsplat is the parent of sparse/0/
    # i.e. it should contain: images/ and sparse/0/{cameras,images,points3D}.bin
    # We need to find or construct this structure.
    data_dir = _prepare_gsplat_data_dir(cfg)

    trainer_script = _find_gsplat_trainer()
    log.info("Using gsplat trainer: %s", trainer_script)

    cmd = [
        "python", str(trainer_script), "default",
        "--data_dir", str(data_dir),
        "--data_factor", "1",
        "--result_dir", str(model_dir),
        "--max_steps", str(cfg.training_steps),
        "--save_ply",
        f"--ply_steps={cfg.training_steps}",
        f"--sh_degree={cfg.sh_degree}",
    ]
    log.info("$ %s", " ".join(cmd))
    subprocess.run(cmd, check=True)

    # gsplat saves as ply/point_cloud_{step}.ply — rename for consistency
    gsplat_ply = model_dir / "ply" / f"point_cloud_{cfg.training_steps - 1}.ply"
    target_ply = cfg.ply_path
    if gsplat_ply.exists() and not target_ply.exists():
        gsplat_ply.rename(target_ply)
        log.info("Renamed PLY → %s", target_ply)

    if not ckpt.exists():
        # gsplat saves ckpt as ckpt_{step}.pt
        log.warning("Checkpoint not found at expected path: %s", ckpt)
        # Try to find it
        for p in sorted(model_dir.glob("ckpt_*.pt"), reverse=True):
            log.info("Found checkpoint: %s", p)
            return p

    return ckpt


def _prepare_gsplat_data_dir(cfg: PipelineConfig) -> Path:
    """Ensure a directory structure gsplat expects:

    data_dir/
      images/   (symlink or copy)
      sparse/0/ (cameras.bin, images.bin, points3D.bin)
    """
    colmap_dir = Path(cfg.colmap_dir)
    image_dir = Path(cfg.image_dir)

    # Check if colmap_dir already has the right structure
    if (colmap_dir / "sparse" / "0" / "cameras.bin").exists() and (
        colmap_dir / "images"
    ).exists():
        return colmap_dir

    # If sparse/0 exists but images/ doesn't, create a symlink
    sparse_dir = colmap_dir / "sparse" / "0"
    if sparse_dir.exists() and not (colmap_dir / "images").exists():
        images_link = colmap_dir / "images"
        images_link.symlink_to(image_dir.resolve())
        log.info("Symlinked %s → %s", images_link, image_dir.resolve())
        return colmap_dir

    # Fallback: the colmap_dir might be the sparse/0 itself
    if (colmap_dir / "cameras.bin").exists():
        # Restructure: create parent with sparse/0 symlink + images
        parent = colmap_dir.parent.parent  # go up from sparse/0
        if not (parent / "images").exists():
            (parent / "images").symlink_to(image_dir.resolve())
        return parent

    raise FileNotFoundError(
        f"Cannot find valid COLMAP data in {colmap_dir}.  "
        f"Expected: sparse/0/cameras.bin, images/"
    )


# ------------------------------------------------------------------
# OpenSplat backend
# ------------------------------------------------------------------

def _train_opensplat(cfg: PipelineConfig) -> Path:
    """Train with OpenSplat (supports Apple Metal, CUDA, CPU)."""
    opensplat = shutil.which("opensplat")
    if opensplat is None:
        raise RuntimeError(
            "opensplat not found on PATH.  "
            "Build from https://github.com/pierotofy/OpenSplat"
        )

    model_dir = Path(cfg.model_dir)
    ply_path = cfg.ply_path

    if ply_path.exists():
        log.info("PLY already exists at %s — skipping training", ply_path)
        return ply_path

    model_dir.mkdir(parents=True, exist_ok=True)

    data_dir = _prepare_gsplat_data_dir(cfg)

    cmd = [
        opensplat, str(data_dir),
        "--output", str(ply_path),
        "-n", str(cfg.training_steps),
        f"--sh-degree={cfg.sh_degree}",
    ]
    log.info("$ %s", " ".join(cmd))
    subprocess.run(cmd, check=True)

    if not ply_path.exists():
        raise RuntimeError(f"OpenSplat did not produce {ply_path}")

    return ply_path
