#!/usr/bin/env python3
"""Parallaxis Phase 1 — 3DGS Reconstruction Pipeline.

End-to-end pipeline: multi-view photos → COLMAP → 3DGS → stereo render → MV-HEVC.

Usage examples:

    # Full pipeline (all steps)
    python -m pipeline.pipeline --scene my_scene

    # Specific steps only
    python -m pipeline.pipeline --scene my_scene --steps sfm,train
    python -m pipeline.pipeline --scene my_scene --steps render,encode

    # Custom viewpoint
    python -m pipeline.pipeline --scene my_scene --steps render,encode \\
        --position 1.0,0.5,2.0 --look-at 0,0,0

    # Render a camera path (spatial video)
    python -m pipeline.pipeline --scene my_scene --steps render,encode \\
        --camera-path orbit --num-frames 60 --output-format video
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
import time
from pathlib import Path

import numpy as np

from .config import PipelineConfig

log = logging.getLogger("parallaxis")

STEPS = ("sfm", "train", "render", "encode")


# ------------------------------------------------------------------
# Camera path generators
# ------------------------------------------------------------------

def generate_orbit_path(
    center: np.ndarray,
    radius: float,
    height: float,
    num_frames: int,
) -> tuple[list[list[float]], list[list[float]]]:
    """Generate a circular orbit camera path around a center point."""
    positions = []
    targets = []
    for i in range(num_frames):
        angle = 2 * math.pi * i / num_frames
        x = center[0] + radius * math.cos(angle)
        z = center[2] + radius * math.sin(angle)
        y = center[1] + height
        positions.append([x, y, z])
        targets.append(center.tolist())
    return positions, targets


def generate_linear_path(
    start: np.ndarray,
    end: np.ndarray,
    target: np.ndarray,
    num_frames: int,
) -> tuple[list[list[float]], list[list[float]]]:
    """Generate a linear camera path from start to end, looking at target."""
    positions = []
    targets = []
    for i in range(num_frames):
        t = i / max(num_frames - 1, 1)
        pos = start + t * (end - start)
        positions.append(pos.tolist())
        targets.append(target.tolist())
    return positions, targets


# ------------------------------------------------------------------
# Main pipeline
# ------------------------------------------------------------------

def run(cfg: PipelineConfig, steps: list[str], camera_path: str | None = None,
        num_frames: int = 60) -> None:
    """Execute the pipeline steps."""
    cfg.resolve()
    t0 = time.time()

    log.info("=" * 60)
    log.info("Parallaxis Phase 1 Pipeline")
    log.info("Scene: %s", cfg.scene_name)
    log.info("Steps: %s", ", ".join(steps))
    log.info("=" * 60)

    # Step 1: SfM
    if "sfm" in steps:
        log.info("")
        log.info("--- Step 1: Structure-from-Motion (%s) ---", cfg.sfm_tool)
        from .colmap_runner import run_sfm
        sparse_dir = run_sfm(cfg)
        log.info("SfM complete: %s", sparse_dir)

    # Step 2: 3DGS Training
    if "train" in steps:
        log.info("")
        log.info("--- Step 2: 3DGS Training (%s, %d steps) ---",
                 cfg.training_backend, cfg.training_steps)
        from .train_gaussians import train
        ckpt = train(cfg)
        log.info("Training complete: %s", ckpt)

    # Step 3: Rendering
    if "render" in steps:
        log.info("")
        if camera_path and cfg.output_format == "video":
            log.info("--- Step 3: Camera Path Rendering (%d frames) ---", num_frames)
            from .render_stereo import render_camera_path
            positions, targets = _build_camera_path(cfg, camera_path, num_frames)
            frames_dir = render_camera_path(cfg, positions, targets)
            log.info("Frames rendered: %s", frames_dir)
        else:
            log.info("--- Step 3: Stereo Pair Rendering ---")
            from .render_stereo import render_stereo
            left, right = render_stereo(cfg)
            log.info("Stereo pair: %s, %s", left, right)

    # Step 4: MV-HEVC Encoding
    if "encode" in steps:
        log.info("")
        log.info("--- Step 4: MV-HEVC Encoding (%s) ---", cfg.output_format)
        from .encode_spatial import encode
        output = encode(cfg)
        log.info("Encoded: %s", output)
        log.info("")
        log.info("Next: AirDrop %s to Vision Pro and open in Photos app.", output.name)

    elapsed = time.time() - t0
    log.info("")
    log.info("Pipeline complete in %.1f seconds.", elapsed)


def _build_camera_path(
    cfg: PipelineConfig,
    path_type: str,
    num_frames: int,
) -> tuple[list[list[float]], list[list[float]]]:
    center = np.array(cfg.camera_look_at, dtype=np.float64)
    pos = np.array(cfg.camera_position, dtype=np.float64)

    if path_type == "orbit":
        radius = float(np.linalg.norm(pos - center))
        height = pos[1] - center[1]
        return generate_orbit_path(center, radius, height, num_frames)
    elif path_type == "linear":
        # Linear from current position to its mirror across the target
        end = 2 * center - pos
        return generate_linear_path(pos, end, center, num_frames)
    else:
        raise ValueError(f"Unknown camera path type: {path_type!r}.  Use 'orbit' or 'linear'.")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def _parse_float_list(s: str) -> list[float]:
    return [float(x.strip()) for x in s.split(",")]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Parallaxis Phase 1 — 3DGS Reconstruction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Scene
    parser.add_argument("--scene", default="my_scene",
                        help="Scene name (default: my_scene)")
    parser.add_argument("--image-dir",
                        help="Override image directory path")

    # Steps
    parser.add_argument("--steps", default=",".join(STEPS),
                        help=f"Comma-separated steps to run (default: {','.join(STEPS)})")

    # SfM
    parser.add_argument("--sfm-tool", choices=["colmap", "glomap", "ns-process-data"],
                        default="colmap", help="SfM backend (default: colmap)")
    parser.add_argument("--multi-camera", action="store_true",
                        help="Images from multiple cameras (different intrinsics)")

    # Training
    parser.add_argument("--backend", choices=["gsplat", "opensplat"],
                        default="gsplat", help="3DGS training backend (default: gsplat)")
    parser.add_argument("--training-steps", type=int, default=30_000,
                        help="Training iterations (default: 30000)")
    parser.add_argument("--sh-degree", type=int, default=3,
                        help="Spherical harmonics degree (default: 3)")

    # Rendering
    parser.add_argument("--width", type=int, default=2048,
                        help="Render width per eye (default: 2048)")
    parser.add_argument("--height", type=int, default=2048,
                        help="Render height per eye (default: 2048)")
    parser.add_argument("--position", type=str, default=None,
                        help="Camera position as x,y,z (default: auto from COLMAP)")
    parser.add_argument("--look-at", type=str, default=None,
                        help="Look-at target as x,y,z (default: scene center)")
    parser.add_argument("--ipd", type=float, default=0.064,
                        help="Interpupillary distance in metres (default: 0.064)")
    parser.add_argument("--fx", type=float, default=1200.0,
                        help="Focal length in pixels (default: 1200, ~80° HFOV at 2048px)")

    # Camera path (for video)
    parser.add_argument("--camera-path", choices=["orbit", "linear"],
                        help="Camera path type for video rendering")
    parser.add_argument("--num-frames", type=int, default=60,
                        help="Number of frames for camera path (default: 60)")

    # Encoding
    parser.add_argument("--output-format", choices=["photo", "video"],
                        default="photo", help="Output format (default: photo)")
    parser.add_argument("--encoder", choices=["spatial", "spatialmediakit"],
                        default="spatial", help="MV-HEVC encoder (default: spatial)")
    parser.add_argument("--bitrate", default="20M",
                        help="Video bitrate (default: 20M)")

    # Misc
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging")

    args = parser.parse_args(argv)

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Build config
    cfg = PipelineConfig(
        scene_name=args.scene,
        sfm_tool=args.sfm_tool,
        single_camera=not args.multi_camera,
        training_backend=args.backend,
        training_steps=args.training_steps,
        sh_degree=args.sh_degree,
        render_width=args.width,
        render_height=args.height,
        ipd=args.ipd,
        fx=args.fx,
        fy=args.fx,  # square pixels
        output_format=args.output_format,
        encoder=args.encoder,
        video_bitrate=args.bitrate,
    )

    if args.image_dir:
        cfg.image_dir = args.image_dir

    if args.position:
        cfg.camera_position = _parse_float_list(args.position)
    if args.look_at:
        cfg.camera_look_at = _parse_float_list(args.look_at)

    steps = [s.strip() for s in args.steps.split(",")]
    for s in steps:
        if s not in STEPS:
            parser.error(f"Unknown step: {s!r}.  Valid: {', '.join(STEPS)}")

    run(cfg, steps, camera_path=args.camera_path, num_frames=args.num_frames)


if __name__ == "__main__":
    main()
