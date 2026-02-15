"""Pipeline configuration."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class PipelineConfig:
    """Configuration for the Parallaxis reconstruction pipeline.

    All paths are relative to the project root (the directory containing this
    pipeline package).  They are resolved to absolute paths by ``resolve()``.
    """

    # ------------------------------------------------------------------
    # Scene
    # ------------------------------------------------------------------
    scene_name: str = "my_scene"

    # ------------------------------------------------------------------
    # Paths (relative to project root, resolved later)
    # ------------------------------------------------------------------
    project_root: str = ""
    image_dir: str = ""
    colmap_dir: str = ""
    model_dir: str = ""
    output_dir: str = ""

    # ------------------------------------------------------------------
    # SfM
    # ------------------------------------------------------------------
    sfm_tool: Literal["colmap", "glomap", "ns-process-data"] = "colmap"
    camera_model: str = "OPENCV"
    single_camera: bool = True

    # ------------------------------------------------------------------
    # 3DGS Training
    # ------------------------------------------------------------------
    training_backend: Literal["gsplat", "opensplat"] = "gsplat"
    training_steps: int = 30_000
    sh_degree: int = 3

    # ------------------------------------------------------------------
    # Stereo Rendering
    # ------------------------------------------------------------------
    render_width: int = 2048
    render_height: int = 2048
    ipd: float = 0.064  # metres
    fx: float = 1200.0
    fy: float = 1200.0

    # ------------------------------------------------------------------
    # Viewpoint (world coordinates)
    # ------------------------------------------------------------------
    camera_position: list[float] = field(default_factory=lambda: [0.0, 0.0, 2.0])
    camera_look_at: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    camera_up: list[float] = field(default_factory=lambda: [0.0, -1.0, 0.0])

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------
    encoder: Literal["spatial", "spatialmediakit"] = "spatial"
    output_format: Literal["photo", "video"] = "photo"
    video_bitrate: str = "20M"
    video_fps: int = 30

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
    @property
    def hfov(self) -> float:
        """Horizontal field-of-view in degrees."""
        return 2 * math.atan(self.render_width / (2 * self.fx)) * 180 / math.pi

    @property
    def cdist(self) -> float:
        """Camera distance in mm (= IPD)."""
        return self.ipd * 1000

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------
    def resolve(self, project_root: Path | None = None) -> "PipelineConfig":
        """Fill in default paths relative to *project_root*.

        Returns *self* for chaining.
        """
        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent
        self.project_root = str(project_root)

        def _default(current: str, default: str) -> str:
            if current:
                return current
            return str(project_root / default)

        self.image_dir = _default(self.image_dir, f"data/scenes/{self.scene_name}/images")
        self.colmap_dir = _default(self.colmap_dir, f"data/colmap/{self.scene_name}")
        self.model_dir = _default(self.model_dir, f"data/models/{self.scene_name}")
        self.output_dir = _default(self.output_dir, f"data/output/{self.scene_name}")
        return self

    @property
    def checkpoint_path(self) -> Path:
        return Path(self.model_dir) / f"ckpt_{self.training_steps - 1}.pt"

    @property
    def ply_path(self) -> Path:
        return Path(self.model_dir) / "point_cloud.ply"
