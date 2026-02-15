"""Step 4 — MV-HEVC spatial photo / video encoding.

Encodes stereo pairs (or frame sequences) into Apple Spatial Photo (.heic) or
Spatial Video (.mov) format using the ``spatial`` CLI or SpatialMediaKit.

Requires macOS 14+ with Apple Silicon.
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
from pathlib import Path

from .config import PipelineConfig

log = logging.getLogger(__name__)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    log.info("$ %s", " ".join(cmd))
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def _check_macos() -> None:
    if platform.system() != "Darwin":
        raise RuntimeError(
            "MV-HEVC encoding requires macOS with Apple Silicon.  "
            "Current platform: " + platform.system()
        )


def _check_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        if name == "spatial":
            raise RuntimeError(
                "'spatial' CLI not found.  Install: brew install spatial  "
                "or download from https://blog.mikeswanson.com/spatial/"
            )
        elif name == "spatial-media-kit-tool":
            raise RuntimeError(
                "'spatial-media-kit-tool' not found.  "
                "Build from https://github.com/sturmen/SpatialMediaKit"
            )
        else:
            raise RuntimeError(f"{name!r} not found on PATH.")
    return path


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def encode(cfg: PipelineConfig) -> Path:
    """Encode stereo output as spatial photo or video.

    Returns the path to the output file.
    """
    if cfg.output_format == "photo":
        return encode_spatial_photo(cfg)
    else:
        return encode_spatial_video(cfg)


# ------------------------------------------------------------------
# Spatial Photo
# ------------------------------------------------------------------

def encode_spatial_photo(cfg: PipelineConfig) -> Path:
    """Encode a single stereo pair as a spatial photo (.heic)."""
    _check_macos()

    output_dir = Path(cfg.output_dir)
    left_png = output_dir / "left.png"
    right_png = output_dir / "right.png"

    if not left_png.exists() or not right_png.exists():
        raise FileNotFoundError(
            f"Stereo pair not found: {left_png}, {right_png}.  "
            "Run the render step first."
        )

    # Convert PNG → HEIC (spatial CLI prefers HEIC)
    left_heic = output_dir / "left.heic"
    right_heic = output_dir / "right.heic"
    for src, dst in [(left_png, left_heic), (right_png, right_heic)]:
        if not dst.exists():
            _run(["sips", "-s", "format", "heic", str(src), "--out", str(dst)])

    out_path = output_dir / "spatial_photo.heic"

    if cfg.encoder == "spatial":
        _encode_photo_spatial_cli(left_heic, right_heic, cfg, out_path)
    else:
        _encode_photo_spatialmediakit(left_heic, right_heic, cfg, out_path)

    log.info("Spatial photo: %s (%.1f MB)", out_path, out_path.stat().st_size / 1e6)
    return out_path


def _encode_photo_spatial_cli(
    left: Path, right: Path, cfg: PipelineConfig, out: Path
) -> None:
    _check_tool("spatial")
    _run([
        "spatial", "make",
        "-i", str(left),
        "-i", str(right),
        "--cdist", f"{cfg.cdist:.1f}",
        "--hfov", f"{cfg.hfov:.1f}",
        "--projection", "rect",
        "-o", str(out),
    ])


def _encode_photo_spatialmediakit(
    left: Path, right: Path, cfg: PipelineConfig, out: Path
) -> None:
    _check_tool("spatial-media-kit-tool")
    # SpatialMediaKit works with video; for photos, use spatial CLI as fallback
    log.warning("SpatialMediaKit does not natively support photos; falling back to spatial CLI")
    _encode_photo_spatial_cli(left, right, cfg, out)


# ------------------------------------------------------------------
# Spatial Video
# ------------------------------------------------------------------

def encode_spatial_video(cfg: PipelineConfig) -> Path:
    """Encode a frame sequence as a spatial video (.mov)."""
    _check_macos()

    output_dir = Path(cfg.output_dir)
    frames_dir = output_dir / "frames"

    if not frames_dir.exists():
        raise FileNotFoundError(
            f"Frames directory not found: {frames_dir}.  "
            "Run render_camera_path first."
        )

    # Check for frames
    left_frames = sorted(frames_dir.glob("left_*.png"))
    right_frames = sorted(frames_dir.glob("right_*.png"))
    if not left_frames or not right_frames:
        raise FileNotFoundError(f"No stereo frames found in {frames_dir}")
    if len(left_frames) != len(right_frames):
        raise ValueError(
            f"Mismatched frame counts: {len(left_frames)} left, {len(right_frames)} right"
        )
    log.info("Found %d stereo frame pairs", len(left_frames))

    # Step A: encode frame sequences → intermediate ProRes videos
    _check_tool("ffmpeg")
    left_mov = output_dir / "left.mov"
    right_mov = output_dir / "right.mov"

    for name, mov_path in [("left", left_mov), ("right", right_mov)]:
        if not mov_path.exists():
            _run([
                "ffmpeg", "-y",
                "-framerate", str(cfg.video_fps),
                "-i", str(frames_dir / f"{name}_%04d.png"),
                "-c:v", "prores_ks", "-profile:v", "3",
                "-pix_fmt", "yuv422p10le",
                str(mov_path),
            ])

    # Step B: encode as MV-HEVC spatial video
    out_path = output_dir / "spatial_video.mov"

    if cfg.encoder == "spatial":
        _encode_video_spatial_cli(left_mov, right_mov, cfg, out_path)
    else:
        _encode_video_spatialmediakit(left_mov, right_mov, cfg, out_path)

    log.info("Spatial video: %s (%.1f MB)", out_path, out_path.stat().st_size / 1e6)
    return out_path


def _encode_video_spatial_cli(
    left: Path, right: Path, cfg: PipelineConfig, out: Path
) -> None:
    _check_tool("spatial")
    _run([
        "spatial", "make",
        "-i", str(left),
        "-i", str(right),
        "--cdist", f"{cfg.cdist:.1f}",
        "--hfov", f"{cfg.hfov:.1f}",
        "--projection", "rect",
        "--primary", "left",
        "--bitrate", cfg.video_bitrate,
        "-o", str(out),
    ])


def _encode_video_spatialmediakit(
    left: Path, right: Path, cfg: PipelineConfig, out: Path
) -> None:
    _check_tool("spatial-media-kit-tool")
    _run([
        "spatial-media-kit-tool", "merge",
        "--left-file", str(left),
        "--right-file", str(right),
        "--quality", "52",
        "--left-is-primary",
        "--horizontal-field-of-view", str(int(cfg.hfov)),
        "--output-file", str(out),
    ])
