"""Step 1 — Structure-from-Motion via COLMAP / GLOMAP.

Estimates camera intrinsics and extrinsics from a set of unordered images.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from .config import PipelineConfig

log = logging.getLogger(__name__)


def _run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    log.info("$ %s", " ".join(cmd))
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def _check_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(
            f"{name!r} not found on PATH.  "
            f"Install it first — see https://colmap.github.io/install.html"
        )
    return path


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def run_sfm(cfg: PipelineConfig) -> Path:
    """Run Structure-from-Motion and return the sparse reconstruction dir.

    Supports three backends:

    * ``colmap``  — calls ``colmap`` CLI directly
    * ``glomap``  — calls ``glomap`` CLI (10-100× faster)
    * ``ns-process-data`` — uses nerfstudio's helper (installs COLMAP for you)
    """
    image_dir = Path(cfg.image_dir)
    output_dir = Path(cfg.colmap_dir)

    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {image_dir}")

    image_count = len(list(image_dir.glob("*.[jJ][pP][gG]")) +
                       list(image_dir.glob("*.[jJ][pP][eE][gG]")) +
                       list(image_dir.glob("*.[hH][eE][iI][cCfF]")) +
                       list(image_dir.glob("*.[pP][nN][gG]")))
    if image_count == 0:
        raise FileNotFoundError(f"No images found in {image_dir}")
    log.info("Found %d images in %s", image_count, image_dir)

    sparse_dir = output_dir / "sparse" / "0"

    # Skip if already done
    if (sparse_dir / "cameras.bin").exists():
        log.info("SfM output already exists at %s — skipping", sparse_dir)
        return sparse_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    if cfg.sfm_tool == "ns-process-data":
        return _run_nerfstudio(image_dir, output_dir)
    elif cfg.sfm_tool == "glomap":
        return _run_glomap(cfg, image_dir, output_dir)
    else:
        return _run_colmap(cfg, image_dir, output_dir)


# ------------------------------------------------------------------
# Backend implementations
# ------------------------------------------------------------------

def _run_colmap(cfg: PipelineConfig, image_dir: Path, output_dir: Path) -> Path:
    _check_tool("colmap")

    db_path = output_dir / "database.db"
    sparse_dir = output_dir / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)

    # Feature extraction
    cmd = [
        "colmap", "feature_extractor",
        "--database_path", str(db_path),
        "--image_path", str(image_dir),
        "--ImageReader.camera_model", cfg.camera_model,
    ]
    if cfg.single_camera:
        cmd += ["--ImageReader.single_camera", "1"]
    _run(cmd)

    # Feature matching
    _run([
        "colmap", "exhaustive_matcher",
        "--database_path", str(db_path),
    ])

    # Sparse reconstruction
    _run([
        "colmap", "mapper",
        "--database_path", str(db_path),
        "--image_path", str(image_dir),
        "--output_path", str(sparse_dir),
    ])

    result_dir = sparse_dir / "0"
    if not result_dir.exists():
        raise RuntimeError(
            "COLMAP mapper did not produce a reconstruction.  "
            "Check that images have sufficient overlap."
        )

    registered = _count_registered(result_dir)
    log.info("COLMAP registered %d images (of ~%d input)", registered, _count_images(image_dir))
    return result_dir


def _run_glomap(cfg: PipelineConfig, image_dir: Path, output_dir: Path) -> Path:
    _check_tool("glomap")
    _check_tool("colmap")  # glomap still needs colmap for feature extraction

    db_path = output_dir / "database.db"
    sparse_dir = output_dir / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)

    # Feature extraction (still via COLMAP)
    cmd = [
        "colmap", "feature_extractor",
        "--database_path", str(db_path),
        "--image_path", str(image_dir),
        "--ImageReader.camera_model", cfg.camera_model,
    ]
    if cfg.single_camera:
        cmd += ["--ImageReader.single_camera", "1"]
    _run(cmd)

    # Feature matching (still via COLMAP)
    _run([
        "colmap", "exhaustive_matcher",
        "--database_path", str(db_path),
    ])

    # Reconstruction via GLOMAP (the fast part)
    _run([
        "glomap", "mapper",
        "--database_path", str(db_path),
        "--image_path", str(image_dir),
        "--output_path", str(sparse_dir),
    ])

    result_dir = sparse_dir / "0"
    if not result_dir.exists():
        raise RuntimeError("GLOMAP mapper did not produce a reconstruction.")
    return result_dir


def _run_nerfstudio(image_dir: Path, output_dir: Path) -> Path:
    _check_tool("ns-process-data")

    _run([
        "ns-process-data", "images",
        "--data", str(image_dir),
        "--output-dir", str(output_dir),
    ])

    result_dir = output_dir / "sparse" / "0"
    if not result_dir.exists():
        # nerfstudio may place it differently
        for candidate in [output_dir / "colmap" / "sparse" / "0", output_dir / "sparse"]:
            if (candidate / "cameras.bin").exists():
                return candidate
        raise RuntimeError("ns-process-data did not produce expected output.")
    return result_dir


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _count_images(image_dir: Path) -> int:
    exts = ("*.jpg", "*.jpeg", "*.png", "*.heic", "*.heif",
            "*.JPG", "*.JPEG", "*.PNG", "*.HEIC", "*.HEIF")
    return sum(len(list(image_dir.glob(e))) for e in exts)


def _count_registered(sparse_dir: Path) -> int:
    """Count registered images in a COLMAP sparse reconstruction."""
    images_bin = sparse_dir / "images.bin"
    if not images_bin.exists():
        return -1
    # Quick heuristic: file size / ~200 bytes per entry
    return max(1, images_bin.stat().st_size // 200)
