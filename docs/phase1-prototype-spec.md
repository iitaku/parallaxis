# Parallaxis Phase 1 Prototype Specification

## 3DGS Reconstruction Pipeline — Feasibility Proof of Concept

**Version:** 1.0
**Date:** 2026-02-15
**Status:** Draft

---

## Table of Contents

1. [Architecture Decision Record](#1-architecture-decision-record)
2. [Prototype Scope](#2-prototype-scope)
3. [Reconstruction Pipeline](#3-reconstruction-pipeline)
4. [Pipeline Automation](#4-pipeline-automation)
5. [Test Content Strategy](#5-test-content-strategy)
6. [Success Criteria](#6-success-criteria)
7. [Future Phases](#7-future-phases)
8. [Reference Repositories](#8-reference-repositories)
9. [Known Risks](#9-known-risks)

---

## 1. Architecture Decision Record

### ADR-001: Cloud Rendering with MV-HEVC Streaming

**Decision:** Parallaxis adopts a **cloud-rendering architecture** where the server reconstructs 3D Gaussian Splatting scenes, renders stereo views for user-selected viewpoints, and delivers the result as MV-HEVC spatial video via HLS to Apple Vision Pro.

**Context:**

The core question for Parallaxis is how to enable free-viewpoint viewing of crowdsourced multi-camera captures on Vision Pro. Two fundamental approaches exist:

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **A: Local 3DGS rendering** | Stream compressed Gaussian data to Vision Pro, render locally on-device | Instant response to head movement, no prediction latency | High client GPU load, immature streaming codecs for dynamic Gaussians, limited by M2 GPU headroom |
| **B: Cloud rendering** | Server renders stereo views for requested viewpoints, streams as standard MV-HEVC video | Minimal client compute (video decode only), mature HLS/MV-HEVC pipeline, works with native AVKit | Latency on viewpoint changes, per-user server rendering cost, requires viewpoint prediction |

**Rationale for choosing Approach B:**

1. **Generative AI compensation is not real-time.** Sparse crowdsourced camera coverage will inevitably produce gaps that require AI-based inpainting/hallucination. Current diffusion-based methods (Deceptive-3DGS, SEVA, NeRFiller) take 1–6 seconds per view — usable as an async quality enhancement pass on the server, but impossible for interactive local rendering.

2. **MV-HEVC/HLS is a mature, native pipeline.** Vision Pro has hardware-accelerated MV-HEVC decode. AVKit, AVExperienceController, and the APMP metadata system provide a battle-tested playback path. No custom Metal rendering required on the client.

3. **Client complexity is minimized.** The Vision Pro viewer becomes a standard immersive video player, reducing development risk and enabling the use of Apple's built-in Photos/TV apps for initial validation.

4. **Migration path to local rendering is preserved.** If device GPU capabilities improve (M5+ Vision Pro) and dynamic Gaussian streaming matures (V3, LapisGS, StreamLoD-GS), the architecture can shift to local rendering without changing the capture or reconstruction pipeline.

**Trade-offs accepted:**

- Viewpoint changes incur network round-trip latency (~200–500ms with prediction)
- Each concurrent viewer requires dedicated server GPU rendering resources
- The experience is "viewpoint design → render" rather than real-time free-viewpoint navigation

### ADR-002: Static Image Feasibility First

**Decision:** Phase 1 validates the reconstruction pipeline using **static multi-view photographs** before attempting video or real-time input.

**Rationale:**

- Static scenes eliminate the need for temporal synchronization, dynamic 3DGS, and real-time processing
- All required OSS tools (COLMAP, gsplat, spatial CLI) are mature and proven for static scenes
- Quality assessment is simpler: no motion artifacts, frame drops, or latency to evaluate
- If static reconstruction fails to produce acceptable spatial photos, the project needs to pivot before investing in real-time infrastructure

---

## 2. Prototype Scope

### 2.1 In Scope

- Multi-view photograph capture (20–50 iPhone photos of a scene)
- Structure-from-Motion camera pose estimation (COLMAP/GLOMAP)
- 3D Gaussian Splatting scene reconstruction (gsplat or OpenSplat)
- Stereo pair rendering from arbitrary viewpoints (gsplat rasterization API)
- MV-HEVC spatial photo/video encoding (spatial CLI or SpatialMediaKit)
- Quality validation on Apple Vision Pro (via Photos app)
- Pipeline automation scripts (Python)

### 2.2 Out of Scope

- Custom visionOS viewer app (use Apple Photos for validation)
- Real-time processing, video input, or live streaming
- iPhone capture app or contributor management
- Generative AI quality enhancement
- HLS streaming server
- WebRTC, authentication, multi-viewer support

### 2.3 Target Architecture (Phase 1 Subset)

```
                      Phase 1 scope
                ┌─────────────────────────┐
                │                         │
                │  iPhone Photos          │
                │  (20-50 multi-view)     │
                │         │               │
                │         ▼               │
                │  COLMAP / GLOMAP        │
                │  (SfM pose estimation)  │
                │         │               │
                │         ▼               │
                │  gsplat / OpenSplat     │
                │  (3DGS training)        │
                │         │               │
                │         ▼               │
                │  Stereo Rendering       │
                │  (arbitrary viewpoint)  │
                │         │               │
                │         ▼               │
                │  spatial CLI            │
                │  (MV-HEVC encoding)     │
                │         │               │
                └─────────┼───────────────┘
                          │
                          ▼
                  Vision Pro Photos App
                  (spatial photo/video)
```

---

## 3. Reconstruction Pipeline

### 3.1 Step 1: Structure-from-Motion (Camera Pose Estimation)

**Purpose:** Estimate camera intrinsic parameters (focal length, lens distortion) and extrinsic parameters (position, orientation) for each input photograph, producing a sparse 3D point cloud.

**Primary tool:** [COLMAP](https://github.com/colmap/colmap)

- The de facto standard for SfM; virtually all 3DGS implementations expect COLMAP output format
- Runs on CPU (any platform: macOS, Linux, Windows)
- For 20–50 images: 5–15 minutes processing time

**Alternative:** [GLOMAP](https://github.com/colmap/glomap)

- 10–100x faster than COLMAP with comparable quality
- Same output format (COLMAP-compatible)
- For 20–50 images: 30 seconds – 3 minutes

**Input:**
```
scene/
└── images/
    ├── IMG_0001.jpg
    ├── IMG_0002.jpg
    ├── ...
    └── IMG_0050.jpg
```

**Output:**
```
scene/
├── images/
│   └── ...
└── sparse/
    └── 0/
        ├── cameras.bin    # Camera intrinsics (focal length, principal point, distortion)
        ├── images.bin     # Camera extrinsics (rotation, translation) per image
        └── points3D.bin   # Sparse 3D point cloud
```

**Command (via nerfstudio helper):**
```bash
ns-process-data images --data ./scene/images --output-dir ./scene/colmap
```

**Command (direct COLMAP):**
```bash
colmap automatic_reconstructor \
    --workspace_path ./scene/colmap \
    --image_path ./scene/images \
    --camera_model OPENCV \
    --single_camera 1
```

Note: `--single_camera 1` assumes all photos come from the same iPhone (same intrinsics). For multi-device capture, omit this flag.

### 3.2 Step 2: 3DGS Reconstruction

**Purpose:** Train a 3D Gaussian Splatting model from the COLMAP output, producing an explicit scene representation as a collection of 3D Gaussians (position, covariance, opacity, spherical harmonics color).

#### Path A: NVIDIA CUDA (Recommended)

**Tool:** [gsplat](https://github.com/nerfstudio-project/gsplat) (JMLR 2025)

- Up to 4x more memory efficient than the original 3DGS implementation
- 15% faster training
- Clean Python API for both training and rendering

**Requirements:**
- NVIDIA GPU with 7+ GB VRAM (RTX 3070+ recommended)
- Python 3.10+, PyTorch 2.0+, CUDA 11.8+

**Command:**
```bash
python simple_trainer.py default \
    --data_dir ./scene/colmap \
    --data_factor 1 \
    --save_ply \
    --ply_steps 30000 \
    --result_dir ./results/scene
```

**Training time:** ~15–30 minutes (30K steps on RTX 3090/4090)

**Output:**
```
results/scene/
├── ckpt_29999.pt              # Checkpoint (PyTorch, used for rendering)
└── ply/
    └── point_cloud_29999.ply  # Exported Gaussians (can be viewed in MetalSplatter)
```

#### Path B: Apple Metal (Mac-only)

**Tool:** [OpenSplat](https://github.com/pierotofy/OpenSplat)

- Cross-platform C++ implementation with Metal acceleration on Mac
- No NVIDIA GPU required
- Licensed AGPLv3

**Requirements:**
- Mac with Apple Silicon (M1+), macOS 13+
- CMake, libtorch

**Command:**
```bash
opensplat ./scene/colmap \
    --output ./results/scene/splat.ply \
    -n 2000 \
    --sh-degree 3
```

**Training time:** ~12 minutes (2K steps on M2 MacBook Pro)

**Output:** `results/scene/splat.ply`

**Note:** OpenSplat produces a `.ply` file but does not provide a Python rendering API. For stereo rendering (Step 3), either:
- Use the exported `.ply` with a custom renderer
- Transfer the `.ply` to a machine with NVIDIA GPU and use gsplat for rendering
- Use MetalSplatter on Vision Pro for interactive viewing (bypasses MV-HEVC encoding)

### 3.3 Step 3: Stereo Pair Rendering

**Purpose:** Render a left-eye and right-eye image from an arbitrary viewpoint in the reconstructed 3DGS scene, simulating the stereo view a Vision Pro user would see.

**Tool:** gsplat `rasterization()` API (requires NVIDIA CUDA)

**Key parameters:**
- **IPD (interpupillary distance):** 64mm (Apple's default for spatial video)
- **Resolution:** 2048×2048 per eye (target; adjustable)
- **FOV:** Computed from camera intrinsics: `hfov = 2 × atan(width / (2 × fx)) × 180 / π`

**Implementation (`render_stereo.py`):**

```python
import torch
import math
import numpy as np
from gsplat import rasterization
from PIL import Image

def load_checkpoint(ckpt_path: str, device: str = "cuda"):
    """Load a trained gsplat checkpoint."""
    ckpt = torch.load(ckpt_path, map_location=device)
    means = ckpt["means"]          # [N, 3] Gaussian centers
    quats = ckpt["quats"]          # [N, 4] Rotations (quaternion)
    scales = ckpt["scales"]        # [N, 3] Scales (log-space)
    opacities = ckpt["opacities"]  # [N] Opacities (logit-space)
    sh0 = ckpt["sh0"]              # [N, 1, 3] DC spherical harmonics
    shN = ckpt["shN"]              # [N, K-1, 3] Higher-order SH
    colors = torch.cat([sh0, shN], dim=1)  # [N, K, 3]
    sh_degree = int(math.sqrt(colors.shape[1]) - 1)
    return means, quats, scales, opacities, colors, sh_degree

def make_stereo_viewmats(
    position: np.ndarray,      # [3] Camera center position in world
    look_at: np.ndarray,       # [3] Point the camera looks at
    up: np.ndarray,            # [3] Up vector (typically [0, 1, 0])
    ipd: float = 0.064,       # Interpupillary distance in meters
    device: str = "cuda",
) -> torch.Tensor:
    """Create left/right view matrices for stereo rendering."""
    # Build camera-to-world rotation
    forward = look_at - position
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, up)
    right = right / np.linalg.norm(right)
    actual_up = np.cross(right, forward)

    # Camera-to-world for center viewpoint
    c2w = np.eye(4)
    c2w[:3, 0] = right
    c2w[:3, 1] = actual_up
    c2w[:3, 2] = -forward  # OpenGL convention: camera looks along -Z
    c2w[:3, 3] = position

    # Offset left and right by half IPD along the right vector
    c2w_left = c2w.copy()
    c2w_left[:3, 3] -= right * (ipd / 2)

    c2w_right = c2w.copy()
    c2w_right[:3, 3] += right * (ipd / 2)

    # Invert to get world-to-camera (view matrices)
    w2c_left = np.linalg.inv(c2w_left)
    w2c_right = np.linalg.inv(c2w_right)

    viewmats = torch.tensor(
        np.stack([w2c_left, w2c_right]),
        dtype=torch.float32,
        device=device,
    )
    return viewmats  # [2, 4, 4]

def render_stereo(
    ckpt_path: str,
    position: np.ndarray,
    look_at: np.ndarray,
    width: int = 2048,
    height: int = 2048,
    fx: float = 1200.0,
    fy: float = 1200.0,
    ipd: float = 0.064,
    output_dir: str = "./output",
):
    """Render a stereo pair from a trained 3DGS checkpoint."""
    device = "cuda"
    means, quats, scales, opacities, colors, sh_degree = load_checkpoint(
        ckpt_path, device
    )

    # View matrices
    viewmats = make_stereo_viewmats(
        position, look_at, up=np.array([0.0, -1.0, 0.0]), ipd=ipd, device=device
    )

    # Intrinsics (same for both eyes)
    cx, cy = width / 2.0, height / 2.0
    K = torch.tensor(
        [[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]],
        dtype=torch.float32,
        device=device,
    )
    Ks = K.unsqueeze(0).expand(2, -1, -1)  # [2, 3, 3]

    # Render both eyes in a single batched call
    with torch.no_grad():
        rendered, alphas, meta = rasterization(
            means, quats, scales, opacities, colors,
            viewmats, Ks, width, height,
            sh_degree=sh_degree,
        )

    # Save images
    for i, name in enumerate(["left", "right"]):
        img = rendered[i].clamp(0, 1).cpu().numpy()
        img_uint8 = (img * 255).astype(np.uint8)
        Image.fromarray(img_uint8).save(f"{output_dir}/{name}.png")

    # Compute HFOV for MV-HEVC metadata
    hfov = 2 * math.atan(width / (2 * fx)) * 180 / math.pi
    print(f"Rendered stereo pair: {width}x{height}, HFOV={hfov:.1f}°, IPD={ipd*1000:.0f}mm")
    return hfov
```

**Viewpoint selection:** The `position` and `look_at` parameters can be set to any 3D coordinate. For best quality, choose viewpoints near (but not identical to) the training camera positions. Viewpoints far from any training camera will show more artifacts.

**Intrinsics note:** The `fx`, `fy` values control the rendered field of view. For Vision Pro spatial video (which has ~63° HFOV on iPhone spatial video), typical values for 2048×2048 output: `fx = fy ≈ 1800` (for ~60° HFOV) or `fx = fy ≈ 1200` (for ~80° HFOV). Adjust based on the desired viewing experience.

### 3.4 Step 4: MV-HEVC Encoding

**Purpose:** Encode the left/right stereo pair as an MV-HEVC spatial photo or spatial video viewable on Apple Vision Pro.

**Requirement:** macOS 14+ (Sonoma) with Apple Silicon (M1+)

#### Spatial Photo (Single Stereo Pair)

**Tool:** [spatial CLI](https://blog.mikeswanson.com/spatial/) — `brew install spatial`

```bash
# Convert PNG to HEIC first (spatial CLI prefers HEIC input)
sips -s format heic output/left.png --out output/left.heic
sips -s format heic output/right.png --out output/right.heic

# Encode as spatial photo
spatial make \
    -i output/left.heic \
    -i output/right.heic \
    --cdist 64.0 \
    --hfov 80.0 \
    --projection rect \
    -o output/spatial_photo.heic
```

Parameters:
- `--cdist 64.0`: Camera distance in mm (= IPD used in rendering)
- `--hfov 80.0`: Horizontal FOV in degrees (must match the rendered FOV)
- `--projection rect`: Rectilinear (perspective) projection

#### Spatial Video (Camera Path Animation)

For a sequence of stereo frames rendered along a camera path:

```bash
# Step A: Render N frames for left and right eyes
# (produces left_0001.png ... left_0300.png, right_0001.png ... right_0300.png)

# Step B: Encode frame sequences to intermediate video
ffmpeg -framerate 30 -i output/frames/left_%04d.png \
    -c:v prores_ks -profile:v 3 output/left.mov
ffmpeg -framerate 30 -i output/frames/right_%04d.png \
    -c:v prores_ks -profile:v 3 output/right.mov

# Step C: Encode as MV-HEVC spatial video
spatial make \
    -i output/left.mov \
    -i output/right.mov \
    --cdist 64.0 \
    --hfov 80.0 \
    --projection rect \
    --primary left \
    --bitrate 20M \
    -o output/spatial_video.mov
```

#### Alternative: SpatialMediaKit (Fully Open Source)

[SpatialMediaKit](https://github.com/sturmen/SpatialMediaKit) provides the same functionality as an open-source Swift tool:

```bash
spatial-media-kit-tool merge \
    --left-file output/left.mov \
    --right-file output/right.mov \
    --quality 52 \
    --left-is-primary \
    --horizontal-field-of-view 80 \
    --output-file output/spatial_video.mov
```

### 3.5 Step 5: Validation on Vision Pro

1. Transfer the spatial photo/video to Vision Pro via AirDrop
2. Open in Apple Photos app
3. The file should appear with a "Spatial" badge and render in stereo
4. Evaluate:
   - **Stereo correctness:** Does the depth feel natural? Is the IPD comfortable?
   - **Visual quality:** Are there visible artifacts (floaters, blurry regions, color banding)?
   - **Viewing angle:** Is the rendered perspective convincing?
   - **Comparison:** How does it compare to an iPhone-captured spatial photo of the same scene?

---

## 4. Pipeline Automation

### 4.1 Directory Structure

```
parallaxis/
├── CLAUDE.md
├── README.md
├── docs/
│   ├── phase1-prototype-spec.md          # This document
│   └── research/
│       └── free-viewpoint-video-systems.md
├── pipeline/
│   ├── requirements.txt                   # Python dependencies
│   ├── pipeline.py                        # Main orchestrator
│   ├── colmap_runner.py                   # COLMAP/GLOMAP execution wrapper
│   ├── train_gaussians.py                 # 3DGS training (gsplat or OpenSplat)
│   ├── render_stereo.py                   # Stereo pair rendering
│   ├── encode_spatial.py                  # MV-HEVC encoding wrapper
│   └── config.py                          # Pipeline configuration dataclass
├── data/                                  # .gitignored
│   ├── scenes/                            # Input photo sets
│   │   └── my_scene/
│   │       └── images/
│   ├── colmap/                            # COLMAP outputs
│   ├── models/                            # Trained 3DGS checkpoints
│   └── output/                            # Rendered spatial photos/videos
└── .gitignore
```

### 4.2 Pipeline Configuration

```python
# config.py
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

@dataclass
class PipelineConfig:
    # Input
    scene_name: str = "my_scene"
    image_dir: str = "data/scenes/my_scene/images"

    # COLMAP
    sfm_tool: str = "colmap"  # "colmap" or "glomap"
    camera_model: str = "OPENCV"
    single_camera: bool = True  # True if all photos from same device

    # 3DGS Training
    training_backend: str = "gsplat"  # "gsplat" or "opensplat"
    training_steps: int = 30000
    sh_degree: int = 3

    # Rendering
    render_width: int = 2048
    render_height: int = 2048
    ipd: float = 0.064  # meters
    fx: float = 1200.0  # Focal length (pixels) — controls FOV
    fy: float = 1200.0

    # Viewpoint (world coordinates)
    camera_position: list = field(default_factory=lambda: [0.0, 0.0, 2.0])
    camera_look_at: list = field(default_factory=lambda: [0.0, 0.0, 0.0])

    # Encoding
    encoder: str = "spatial"  # "spatial" or "spatialmediakit"
    output_format: str = "photo"  # "photo" or "video"
    video_bitrate: str = "20M"

    # Paths (derived)
    @property
    def colmap_dir(self) -> str:
        return f"data/colmap/{self.scene_name}"

    @property
    def model_dir(self) -> str:
        return f"data/models/{self.scene_name}"

    @property
    def output_dir(self) -> str:
        return f"data/output/{self.scene_name}"

    @property
    def hfov(self) -> float:
        import math
        return 2 * math.atan(self.render_width / (2 * self.fx)) * 180 / math.pi
```

### 4.3 Main Pipeline Script

```python
# pipeline.py (pseudo-code structure)
"""
Parallaxis Phase 1 Pipeline

Usage:
    python pipeline.py --scene my_scene
    python pipeline.py --scene my_scene --steps sfm,train,render,encode
    python pipeline.py --scene my_scene --render-only --position 1.0,0.5,2.0 --look-at 0,0,0
"""

def run_pipeline(config: PipelineConfig, steps: list[str]):
    if "sfm" in steps:
        run_colmap(config)          # Step 1: Camera pose estimation

    if "train" in steps:
        train_gaussians(config)     # Step 2: 3DGS training

    if "render" in steps:
        render_stereo_pair(config)  # Step 3: Stereo rendering

    if "encode" in steps:
        encode_spatial(config)      # Step 4: MV-HEVC encoding

    print(f"Output: {config.output_dir}/spatial_photo.heic")
    print("Transfer to Vision Pro via AirDrop for validation.")
```

### 4.4 Dependencies

```
# requirements.txt
torch>=2.0.0
gsplat>=1.0.0
numpy>=1.24.0
Pillow>=10.0.0
```

External tools (installed separately):
- COLMAP: `brew install colmap` or [build from source](https://colmap.github.io/install.html)
- GLOMAP: [build from source](https://github.com/colmap/glomap)
- spatial CLI: `brew install spatial` (macOS only)
- FFmpeg: `brew install ffmpeg` (for video encoding path)
- OpenSplat: [build from source](https://github.com/pierotofy/OpenSplat) (Mac Metal path)

---

## 5. Test Content Strategy

### 5.1 Phase 1a: Tabletop Object (Simplest)

- Place an object (figurine, plant, coffee mug) on a table
- Walk around and take 30–50 photos from different angles
- Coverage: 360° around the object, some elevated angles
- This is the standard benchmark scenario for 3DGS

### 5.2 Phase 1b: Indoor Room

- Photograph a room interior from multiple positions
- 30–50 photos covering the main features
- Tests: larger scale, more complex geometry, lighting variation

### 5.3 Phase 1c: Outdoor / Venue-like Space

- Small outdoor area (courtyard, park bench, street corner)
- Tests: natural lighting, sky, vegetation (challenging for 3DGS)
- Closer to the eventual target of venue-scale reconstruction

### 5.4 Capture Guidelines

- **Overlap:** Aim for 60–80% overlap between adjacent viewpoints
- **Coverage:** Cover the subject from as many angles as possible; avoid large gaps
- **Stability:** Hold the phone steady; avoid motion blur
- **Exposure:** Let auto-exposure work; avoid extreme lighting variation between shots
- **Resolution:** Full iPhone resolution (12MP+); do not crop
- **Format:** HEIF or JPEG (COLMAP handles both)
- **Quantity:** 20 photos minimum, 50 recommended, more is generally better
- **Avoid:** Reflective surfaces (glass, mirrors), moving objects, uniform textureless walls

---

## 6. Success Criteria

### 6.1 P0 — Must Have

| # | Criterion | Validation Method |
|---|-----------|-------------------|
| 1 | Reconstruct a 3DGS scene from 20–50 iPhone photos | COLMAP produces sparse reconstruction + gsplat training completes without errors |
| 2 | Render a stereo pair from a viewpoint NOT in the training set | Visual inspection: rendered image shows the scene from a novel angle |
| 3 | Encode the stereo pair as an MV-HEVC spatial photo | `spatial make` or SpatialMediaKit produces a valid `.heic` file |
| 4 | View the spatial photo on Vision Pro in Apple Photos | File displays with "Spatial" badge, renders in stereo with correct depth |
| 5 | Visual quality is sufficient for concept validation | Subjective: stereo depth feels natural, scene is recognizable, no severe artifacts |

### 6.2 P1 — Should Have

| # | Criterion | Validation Method |
|---|-----------|-------------------|
| 6 | Render a camera path animation as spatial video | Multiple frames rendered, encoded as `.mov`, plays as spatial video on Vision Pro |
| 7 | Pipeline runs end-to-end with a single command | `python pipeline.py --scene my_scene` completes all steps |
| 8 | Quality tuning guide documented | Document the effect of training steps, SH degree, resolution, and viewpoint distance on quality |

### 6.3 P2 — Nice to Have

| # | Criterion | Validation Method |
|---|-----------|-------------------|
| 9 | Mac-only pipeline (no NVIDIA GPU) | OpenSplat training + custom Metal rendering works end-to-end |
| 10 | Multiple viewpoints from same scene | Generate a "virtual tour" spatial video from 5+ viewpoints |
| 11 | A/B comparison with iPhone spatial capture | Side-by-side quality comparison: 3DGS-rendered vs iPhone-captured spatial photo of same scene |

---

## 7. Future Phases

### Phase 2: Video Input & Viewpoint Selection UI

- Accept video input (extract frames, handle temporal redundancy)
- Explore 4D Gaussian Splatting for dynamic scenes
- Build a web-based viewpoint selection UI (3D venue map, click to select viewpoint, server renders)
- Initial HLS streaming of rendered spatial video

### Phase 3: iPhone Real-time Capture & Server Ingest

- iPhone capture app: ARKit 6DoF pose + HEVC video stream + camera intrinsics
- Server ingest service: multi-device stream reception and frame alignment
- NTP-based time synchronization across devices
- Session management: create/join events, device discovery

### Phase 4: Real-time Reconstruction & AI Enhancement

- Replace COLMAP with ARKit-derived poses (eliminate SfM latency)
- Incremental 3DGS optimization (update scene as new frames arrive)
- Generative AI quality enhancement for sparse regions:
  - Depth Anything V2 for per-frame monocular depth
  - Diffusion-based inpainting for coverage gaps (async quality improvement)
  - Deceptive-3DGS style pseudo-observation generation

### Phase 5: Production Streaming & visionOS Viewer

- Custom visionOS viewer app (Swift/SwiftUI, AVKit + AVExperienceController)
- Low-latency HLS streaming (CMAF-LL, target < 2s glass-to-glass)
- Viewpoint request → server render → stream feedback loop
- Coverage heatmap UI: show where camera density supports high quality
- Multi-viewer support (multiple Vision Pro users, one event)

---

## 8. Reference Repositories

### Core Pipeline Tools

| Repository | Purpose | Platform |
|------------|---------|----------|
| [colmap/colmap](https://github.com/colmap/colmap) | Structure-from-Motion | Any (CPU) |
| [colmap/glomap](https://github.com/colmap/glomap) | Faster SfM (10–100x) | Any (CPU) |
| [nerfstudio-project/gsplat](https://github.com/nerfstudio-project/gsplat) | 3DGS training & rendering | NVIDIA CUDA |
| [nerfstudio-project/nerfstudio](https://github.com/nerfstudio-project/nerfstudio) | Full framework (Splatfacto method) | NVIDIA CUDA |
| [pierotofy/OpenSplat](https://github.com/pierotofy/OpenSplat) | Cross-platform 3DGS (Metal) | Mac / NVIDIA / CPU |
| [sturmen/SpatialMediaKit](https://github.com/sturmen/SpatialMediaKit) | MV-HEVC encoding (open source) | macOS Apple Silicon |
| [mikeswanson/spatial](https://blog.mikeswanson.com/spatial/) | MV-HEVC encoding CLI | macOS Apple Silicon |

### Related / Reference

| Repository | Purpose | Notes |
|------------|---------|-------|
| [graphdeco-inria/gaussian-splatting](https://github.com/graphdeco-inria/gaussian-splatting) | Original 3DGS (SIGGRAPH 2023) | Reference implementation |
| [scier/MetalSplatter](https://github.com/scier/MetalSplatter) | 3DGS viewer for Vision Pro | Alternative validation: load .ply directly |
| [mikeswanson/SpatialPlayer](https://github.com/mikeswanson/SpatialPlayer) | MV-HEVC player for visionOS | Reference for future viewer app |
| [apple/ml-sharp](https://github.com/apple/ml-sharp) | Single-image → 3DGS | Potential future use for sparse input enhancement |
| [iffyloop/gsplat-mps](https://github.com/iffyloop/gsplat-mps) | gsplat on Apple MPS | Experimental Mac rendering |

### Key Research Papers

- Kerbl et al., "3D Gaussian Splatting for Real-Time Radiance Field Rendering" (SIGGRAPH 2023)
- Wu et al., "4D Gaussian Splatting for Real-Time Dynamic Scene Rendering" (CVPR 2024)
- Ye et al., "gsplat: An Open-Source Library for Gaussian Splatting" (JMLR 2025)

### Internal Documentation

- [`docs/research/free-viewpoint-video-systems.md`](./research/free-viewpoint-video-systems.md) — Comprehensive survey of FVV systems, sparse reconstruction methods, data formats, Vision Pro capabilities, and streaming approaches

---

## 9. Known Risks

### 9.1 Scale Ambiguity

**Risk:** COLMAP output is in an arbitrary coordinate system, not metric scale. The IPD (64mm) must be applied in the correct scale for natural stereo depth on Vision Pro.

**Mitigation:**
- Include a known-size reference object in the scene (e.g., a ruler, standard A4 paper)
- Compute the scale factor by measuring a known distance in the COLMAP point cloud
- Alternatively, adjust IPD relative to the COLMAP scale rather than converting to metric

### 9.2 NVIDIA GPU Dependency

**Risk:** The primary pipeline path (gsplat) requires NVIDIA CUDA. Mac users cannot run the full pipeline locally.

**Mitigation:**
- OpenSplat provides Metal-accelerated training on Mac (but no Python rendering API)
- Cloud GPU instances (e.g., AWS g5, Lambda Cloud, RunPod) can be used for training and rendering
- The gsplat-mps fork provides experimental Apple MPS support (older gsplat version)
- MetalSplatter on Vision Pro provides an alternative validation path (load .ply directly, no MV-HEVC encoding needed)

### 9.3 Novel Viewpoint Quality

**Risk:** Viewpoints far from any training camera will show artifacts: floaters (stray Gaussians in empty space), blurry regions, color inconsistencies.

**Mitigation:**
- Start with viewpoints close to training cameras and gradually move further
- Increase the number of input photos for better coverage
- Apply post-processing: anti-aliasing with Mip-Splatting techniques (integrated in recent gsplat versions)
- Document the "quality radius" — the distance from training cameras within which quality is acceptable

### 9.4 MV-HEVC Encoding Platform Lock

**Risk:** MV-HEVC encoding with proper Apple spatial metadata requires macOS + Apple Silicon. The encoding step cannot run on Linux servers.

**Mitigation:**
- Phase 1 is a PoC; encoding on a local Mac is acceptable
- For future phases: investigate programmatic MV-HEVC encoding via VideoToolbox on macOS build machines
- Alternative: render side-by-side stereo and convert server-side using FFmpeg (loses some Apple-specific metadata, but basic stereo works)

### 9.5 COLMAP Failure Modes

**Risk:** COLMAP may fail to register all images if there is insufficient overlap, if the scene has large textureless regions, or if images have inconsistent exposure.

**Mitigation:**
- Follow the capture guidelines (60–80% overlap, varied angles)
- Use `--camera_model OPENCV` and `--single_camera 1` for single-device capture
- If COLMAP fails, try GLOMAP (handles some failure cases better)
- Inspect the sparse reconstruction before proceeding to 3DGS training
