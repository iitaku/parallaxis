# Free-Viewpoint Video (FVV) Systems & Volumetric Video Technologies

Research compiled: February 2026

---

## 1. Commercial Free-Viewpoint Video Systems

### 1.1 Intel True View (2016-2021, DISCONTINUED)

**Status:** Discontinued in August 2021. Intel shut down its sports division and sold parts to Verizon.

**How it worked:**
- **Camera array:** Up to 38 JAI 5K ultra-high-definition cameras installed permanently around a stadium
- **Capture method:** Cameras captured height, width, and depth data to produce voxels (pixels with volume)
- **Processing:** Massive server infrastructure powered by Intel Xeon processors processed volumetric data
- **Representation:** Voxel-based volumetric reconstruction. Created fully volumetric 3D models enabling 6DOF viewing
- **Output:** Virtual camera positions could be defined by operators — stationary, rail, and tracking cameras that followed objects (ball, players)
- **Latency:** Cloud-based rendering pipeline; not truly real-time for arbitrary viewpoints, but replays could be generated quickly

**Deployment scale:**
- 19 NFL stadiums
- ~12 European soccer venues (Liverpool, Arsenal, Barcelona, Real Madrid)
- NBA arenas
- 2024 Paris Olympics (related technology, not True View specifically)

**Why it was discontinued:** Intel's new CEO Pat Gelsinger refocused the company on core semiconductor business. Intel stated it was "removing volumetric video from Intel's roadmap to focus on advancing innovative technologies that better support our core businesses and IDM 2.0 strategy."

**Data format:** Proprietary voxel-based format. Point clouds computed from multi-view images, then rendered to virtual camera views on the server side.

**Key technical details:**
- Earlier development used Intel RealSense R200 depth sensors (640x480), later upgraded
- Processing on Intel Xeon E5-2699 v3 + NVIDIA GeForce GTX 970 GPU (early versions)
- Production pipeline included virtual camera tools for operators to place/control cameras in 3D space

**Source:** [Planet Analog](https://www.planetanalog.com/are-you-ready-for-some-3d-football-intel-true-view-technology/), [VentureBeat](https://venturebeat.com/2019/09/19/intel-true-view-is-a-cool-technology-for-immersive-sports-viewing/), [Calcalist Tech](https://www.calcalistech.com/ctech/articles/0,7340,L-3915635,00.html)

---

### 1.2 Canon Free Viewpoint Video System (2016-present, ACTIVE)

**How it works:**
- **Camera array:** 30 cameras (demo) to 100+ Canon Cinema EOS cameras and lenses (production, e.g., Barclays Center NBA installation)
- **Edge processing:** Each camera has a dedicated AMD Versal AI Core image-processing box running proprietary Canon ML algorithms for detection and segmentation at the edge
- **Representation:** Point-cloud 3D model. Video from all cameras is processed and turned into data on proprietary Canon image-processing hardware, then sent to a server that creates a point-cloud 3D model
- **Synchronization:** Proprietary algorithms ensure all cameras start shooting at the exact same time — if timing is off for even one camera, data cannot be generated correctly
- **Latency:** Near real-time replays (~3 second delay demonstrated for NBA broadcasts), down from minutes with traditional architectures

**Key deployments:**
- J.LEAGUE Cup Final (2016, debut)
- Rugby World Cup 2019
- Barclays Center, Brooklyn (100+ cameras, full NBA game production for ESPN+)
- Canon Volumetric Video Studio in Kawasaki (2020)

**Production workflow:** Operators use virtual camera tools to define viewpoints. The ESPN NBA CourtView broadcast was described as "like watching NBA2K on steroids, with sweeping camera views from nearly any angle."

**Data format:** Proprietary point-cloud format, rendered to 2D views server-side for broadcast.

**Source:** [Canon Global Technology](https://global.canon/en/technology/volumetric-video2023.html), [AMD Newsroom](https://www.amd.com/en/newsroom/press-releases/2022-6-28-amd-powers-real-time-ai-processing-at-the-edge-for.html), [SVG](https://www.sportsvideo.org/2022/03/21/canon-free-viewpoint-tech-used-for-espn-full-nba-game-production/)

---

### 1.3 4DReplay (ACTIVE — Time-slice/Bullet-time)

**Technology:** 4DReplay produces 360-degree time-slice highlights (rotating freeze-frame replays), not full free-viewpoint video. Closer to "bullet time" than true 6DOF FVV.

- **Cameras:** Arrays of 4K cameras synchronized through existing broadcast infrastructure
- **Processing:** Series of industry-leading processors, consoles, and hubs syncing through broadcast lines
- **Output:** Time-frozen rotating highlights, not arbitrary viewpoint synthesis

**Key deployments:** Olympics, NHL All-Star, MLB Home Run Derby, PGA Championship, FIFA U-20 World Cup. Broadcast partners include CBS, ESPN, NBC, France TV, TF1, Fuji TV, KBSN.

**Source:** [4DReplay](https://4dreplay.com/)

---

### 1.4 4DViews / HOLOSYS (ACTIVE — Studio Volumetric Capture)

**Technology:** Turnkey studio-based volumetric video capture system. Unlike stadium systems, this is designed for controlled studio environments with green screen.

- **Camera array:** HOLOSYS uses 32 or 48 synchronized cameras
- **HOLOSYS+ (2023):** Next-generation with increased texture quality, larger capture zone (up to 3 people), upgraded hardware
- **Capture method:** Multi-angle simultaneous capture in green screen environment; frame-by-frame geometry generation
- **Output formats:** Proprietary .4DS format, or generic .ABC (Alembic) for VFX/CGI pipelines
- **Platform support:** AR, VR, MR, 2D — with Unity, Unreal, and WebXR plugins
- **Studio network:** 20+ studios worldwide

**Limitations:** Studio-only (requires green screen, controlled lighting). Maximum 3 people captured simultaneously (occlusion constraints).

**Source:** [4DViews](https://www.4dviews.com/), [3DVF SIGGRAPH Report](https://3dvf.com/en/siggraph-2023-4dviews-unveils-cutting-edge-volumetric-capture-system-holosys/)

---

### 1.5 Microsoft Mixed Reality Capture Studios → Arcturus (2010-present)

**How it worked (Microsoft era):**
- **Camera array:** 100+ cameras (106 mentioned specifically) working in unison, including infrared depth sensors
- **Capture space:** ~8 feet diameter, 10 feet height (portable setup)
- **Processing:** Sophisticated reconstruction software creating photorealistic 3D video
- **Output:** Holograms for HoloLens, VR, VFX, live broadcasts
- **Limitations:** IR sensors had problems with shiny materials, black materials, leather, glass, plastics

**Transition (2023):** Arcturus became sole provider for MRCS technology at SIGGRAPH 2023. Arcturus integrated MRCS with its own HoloSuite tools.

**Arcturus codecs (current):**
1. **OMS (Open Mesh Sequence):** Mesh compression via bitpacking + skeletal retargeting. MP4 container packaging mesh + texture. Supported in Unity via HoloSuite Player plugin.
2. **AVV (Accelerated Volumetric Video, 2024):** High-performance codec with texture analysis, normals transfer, smart texture (prioritizes facial features), motion vectors. Supports LOD similar to game engines. Significantly compressed while maintaining quality.

**Source:** [Variety](https://variety.com/2018/digital/features/microsoft-mixed-reality-capture-behind-the-scenes-1202784950/), [Arcturus](https://arcturus.studio/blog/arcturus-volumetric-video-codec/), [Digital Media World](https://www.digitalmediaworld.tv/production/arcturus-new-codec-scales-volumetric-video-data-for-real-time-playback)

---

### Commercial Systems Summary Table

| System | Cameras | Environment | Representation | Status | Real-time? |
|--------|---------|-------------|----------------|--------|------------|
| Intel True View | 38 x 5K | Stadium (permanent) | Voxels/point clouds | Discontinued 2021 | Near-real-time replays |
| Canon Free Viewpoint | 30-100+ Cinema EOS | Stadium (permanent) | Point clouds | Active | ~3s delay |
| 4DReplay | Array of 4K | Stadium | Time-slice images | Active | Replays only |
| 4DViews HOLOSYS | 32-48 | Studio (green screen) | Mesh + texture (.4DS) | Active | Near-real-time |
| Microsoft/Arcturus | 100+ | Studio (portable) | Mesh + texture (OMS/AVV) | Active (Arcturus) | Post-processing |

---

## 2. Sparse Camera Systems & Minimum Camera Counts

### 2.1 Minimum Camera Requirements (Research Findings)

The minimum camera count for acceptable free-viewpoint quality depends heavily on the scene, rendering method, and desired quality:

**With neural priors (learning-based):**
- **2 views:** Possible with learned priors (e.g., diffusion model hallucination), but limited to static/simple scenes. High GPU requirements. Not yet demonstrated for full dynamic scene reconstruction.
- **4 cameras:** "Holoported Characters" (Max Planck Institute) demonstrates 4K resolution real-time free-viewpoint video of human actors from only 4 RGB cameras. Handles wide clothing, reproduces wrinkles, expressions, hand gestures. **Caveat:** Training requires dense multi-view video and a rigged static surface scan.
- **6-12 cameras:** Practical minimum for reasonable quality with modern sparse-view methods (FreeSplatter, MVSplat, InstantSplat). Acceptable for human subjects with some artifacts.

**Traditional (non-neural) methods:**
- **20-40 cameras:** Minimum for traditional MVS approaches to produce acceptable free-viewpoint video
- **100+ cameras:** Standard for commercial studio quality

**Key factors affecting minimum count:**
- Inter-camera distance (baseline) significantly affects view quality
- Occlusion: regions invisible from neighboring cameras degrade depth estimation and synthesis
- Scene complexity: more cameras needed for complex geometry, transparent/reflective surfaces
- Desired output resolution and viewpoint range

### 2.2 Sparse vs. Dense Trade-offs

| Aspect | Dense (50-100+) | Moderate (12-30) | Sparse (2-8) |
|--------|-----------------|-------------------|---------------|
| Quality | Professional broadcast | Acceptable with neural methods | Requires strong priors, artifacts visible |
| Coverage | Full scene | Most of scene | Significant gaps |
| Cost | Very high ($1M+) | Moderate | Low |
| Robustness | Handles occlusion well | Some occlusion issues | Heavy reliance on hallucination |
| Processing | Traditional MVS works | Need learning-based methods | Feed-forward neural models required |

### 2.3 Key Sparse-View Research (2024-2025)

**Feed-forward methods (no per-scene training):**
- **FreeSplatter (ICCV 2025):** Generates 3D Gaussians from uncalibrated sparse views + recovers camera parameters in seconds. Transformer-based multiview exchange.
- **MVSplat (ECCV 2024 Oral):** Efficient feed-forward 3DGS from sparse multi-view. Strong generalization to out-of-distribution scenes via cost volume features.
- **MV-DUSt3R+:** Single-stage feedforward for dense 3D reconstruction from sparse unposed RGB. Produces point clouds and camera poses in <2 seconds.
- **InstantSplat:** Pose-free Gaussian splatting in ~40 seconds using DUSt3R for geometric initialization.
- **SparSplat:** State-of-the-art 3D reconstruction and novel view synthesis from sparse, uncalibrated inputs with fast inference.

**Key trend:** The field is moving rapidly toward **pose-free, feed-forward** methods that can reconstruct from uncalibrated sparse views without per-scene optimization. This is directly relevant to Parallaxis's crowdsourced camera model.

**Source:** [Frontiers in Signal Processing](https://www.frontiersin.org/journals/signal-processing/articles/10.3389/frsip.2025.1405808/full), [Holoported Characters (arXiv)](https://arxiv.org/abs/2312.07423), [FreeSplatter (GitHub)](https://github.com/TencentARC/FreeSplatter), [MVSplat (GitHub)](https://github.com/donydchen/mvsplat)

---

## 3. Data Representation Formats

### 3.1 Point Clouds

**Formats:** PLY, LAS/LAZ, PCD, XYZ, E57

**Characteristics:**
- Sets of 3D points with attributes (color, normals, reflectance)
- Faster/easier to obtain than meshes (lower computational complexity)
- Can represent any geometry without topology constraints
- Raw point clouds are bandwidth-heavy: a 200K-point frame at 30fps can demand ~720 Mbps uncompressed

**Compression standards:**
- **V-PCC (Video-based PCC, ISO/IEC 23090-5):** Projects 3D point clouds onto 2D images, then uses standard video codecs (HEVC). Achieves 100:1 to 300:1 compression. 1M points encoded at ~8 Mbps with good quality. Real-time decoding demonstrated on mobile hardware.
- **G-PCC (Geometry-based PCC, ISO/IEC 23090-9):** Directly compresses 3D geometry. Better for static and LiDAR point clouds.
- **Draco (Google):** Fast but V-PCC achieves 100x better compression ratio.

**Best for:** Dense capture systems, LiDAR data, intermediate representations

### 3.2 Textured Meshes

**Formats:** OBJ, FBX, glTF/GLB, Alembic (.ABC), USD/USDZ

**Characteristics:**
- Watertight surface representation with UV-mapped textures
- More bandwidth-efficient than point clouds at high quality (>50 Mbps regime)
- Standard game engine and RealityKit support
- Can be generated from point clouds via surface reconstruction (Poisson, etc.)

**Volumetric video mesh codecs:**
- **Arcturus OMS:** Mesh sequence in MP4 container with bitpacking compression
- **Arcturus AVV (2024):** High-performance mesh+texture codec with LOD, normals transfer, motion vectors
- **4DViews .4DS:** Proprietary optimized mesh sequence format
- **Draco mesh compression:** Standard open-source mesh compression

**Best for:** Studio-captured content, game engine integration, established pipelines

### 3.3 3D Gaussian Splats

**Formats:** PLY (standard), SPZ (Niantic), SOG/SOGS (PlayCanvas), Compressed PLY, .splat

**Characteristics:**
- Explicit representation: each Gaussian has position, covariance (scale + rotation), opacity, color (SH coefficients)
- Real-time novel view synthesis via differentiable rasterization
- Standard PLY files are large (250MB+ for detailed scenes) — SH coefficients consume ~75% of storage
- Highly parallelizable rendering, well-suited to GPU

**Compression formats:**
- **PLY (uncompressed):** ~60 bytes/splat (position + SH + scale + rotation + opacity). Scenes typically 100K-5M splats.
- **Compressed PLY (PlayCanvas/SuperSplat):** ~4x smaller via quantization per chunk (256 splats grouped by locality).
- **SPZ (Niantic/Scaniverse):** ~10x smaller than PLY. Uses fixed-point quantization (24-bit positions), log encoding for scales, 8-bit SH with reduced precision. Column-based layout + gzip.
- **SOG/SOGS (PlayCanvas):** ~15-20x smaller. Reshapes attributes into 2D "attribute images" and applies WebP compression. Innovative but complex.
- **Progressive SH:** Drop higher SH bands for lower quality tiers. SH0 only = ~4x smaller, minimal quality loss for distant/non-reflective content.

**Dynamic 4D Gaussian methods (2024-2025):**
- **4D Gaussian Splatting (CVPR 2024):** Canonical 3D Gaussians + deformation field. 82 FPS at 800x800 on RTX 3090.
- **Native 4D Gaussians (ICLR 2024):** Direct 4D primitives modeling spatiotemporal volume.
- **MEGA (ICCV 2025):** Memory-efficient 4D Gaussian splatting for dynamic scenes.
- **Deformable 3DGS variants:** SC-GS (sparse-controlled), MD-Splatting (highly deformable).

**Best for:** Novel view synthesis, real-time rendering, emerging streaming paradigm

### 3.4 Neural Implicit Representations

**Formats:** Model weights (PyTorch checkpoints), ONNX, custom serialization

**Characteristics:**
- NeRF and variants encode scenes as neural network weights
- Highest quality per-scene but slow to train and render
- Not easily streamable (entire model needed)
- Dynamic variants exist: D-NeRF, K-Planes, HexPlane, temporal tri-plane

**Compression research:**
- TeTriRF, ReRF: Quantization + 3D-to-2D conversion + video codec pipelines for orders-of-magnitude compression
- Still primarily a research representation, not production-ready for streaming

**Best for:** Highest-quality offline rendering, research prototypes

### 3.5 Volumetric Video Codecs (MPEG-I Family)

**V3C (Visual Volumetric Video-based Coding, ISO/IEC 23090-5):**
- Common framework supporting point clouds (V-PCC) and immersive video (MIV)
- V-PCC: Projects 3D to 2D, leverages HEVC. 100:1-300:1 compression.
- MIV: Multi-view video with depth. Supports equirectangular, perspective, orthographic projections. ~25 Mbps for HEVC.
- 4th edition in development; Brazil TV 3.0 deployment planned 2025.

**MPEG working on radiance field compression:**
- Future standard development for radiance field representation and compression (as of 2025).

**Best for:** Standards-based delivery, broadcast integration, interoperability

### 3.6 Format Comparison for Streaming to a Headset

| Format | Streaming Suitability | Bandwidth | Client Compute | Quality | Maturity |
|--------|----------------------|-----------|----------------|---------|----------|
| Point clouds (V-PCC) | Good (standard codecs) | ~8-50 Mbps | Medium | Good | Standardized |
| Textured meshes (AVV) | Good (mesh+texture in MP4) | ~20-80 Mbps | Low (standard GPU) | High | Commercial |
| 3D Gaussians (SPZ) | Emerging (progressive LOD) | ~5-30 Mbps | Medium-High | Very High | Early |
| MIV (multi-view+depth) | Good (HEVC-based) | ~25 Mbps | Low | Good | Standardized |
| Neural implicit | Poor (need full model) | Low once loaded | Very High | Highest | Research |
| Cloud-rendered 2D | Excellent (standard video) | ~5-15 Mbps | Very Low | Depends on prediction | Proven |

**Source:** [MPEG PCC Overview](https://mpeg-pcc.org/wp-content/uploads/2020/04/an_overview_of_ongoing_point_cloud_compression_standardization_activities_videobased_vpcc_and_geometrybased_gpcc.pdf), [PlayCanvas Compression Blog](https://blog.playcanvas.com/compressing-gaussian-splats/), [Scaniverse SPZ](https://scaniverse.com/news/spz-gaussian-splat-open-source-file-format), [Arcturus AVV](https://arcturus.studio/blog/arcturus-volumetric-video-codec/)

---

## 4. Apple Vision Pro Capabilities

### 4.1 Hardware Specifications

**Original Vision Pro (M2, launched Feb 2024):**
- M2 chip: 8-core CPU, 10-core GPU, 16-core Neural Engine
- 16GB unified memory
- R1 chip: Dedicated sensor processing (cameras, eye tracking, spatial audio)
- Metal 3 support, hardware mesh shading
- Display: 23M pixels across two micro-OLED panels, 90Hz refresh rate

**M5 Vision Pro (2025 upgrade):**
- 10-core GPU with hardware-accelerated ray tracing
- 16-core Neural Engine (50% faster AI than M2)
- ~2.5x faster graphics vs M1, ~30% faster vs M4

**Key constraint:** The GPU must simultaneously handle passthrough rendering, eye tracking, foveated rendering, and app graphics. Available headroom for custom volumetric rendering is limited.

### 4.2 Can Vision Pro Render Point Clouds in Real-Time?

**Yes, via LowLevelMesh API (visionOS 2+):**
- `LowLevelMesh` allows custom vertex buffer layouts updated by Metal compute shaders
- Supports `.point` primitive topology or billboard quads per point
- GPU-driven updates: dispatch Metal compute kernels to populate vertex buffers, RealityKit waits on completion before rendering
- Must pre-allocate buffers with maximum expected point count
- Works in shared/mixed immersive spaces (not just full immersion)

**Practical limits:** No published benchmarks for point count limits, but the M2's 10-core GPU and 16GB unified memory should handle hundreds of thousands of points at interactive rates.

### 4.3 Can Vision Pro Render 3D Gaussians in Real-Time?

**Yes, proven by multiple shipping apps:**

| App | Open Source? | Formats | Features |
|-----|-------------|---------|----------|
| **MetalSplatter** | Yes (library) | PLY, SPZ, .splat | Full SH3, stereo via amplification, AR mode (visionOS 2) |
| **Spatial Fields** | No | PLY, SPZ | Frustum culling, GPU path, dynamic LOD, on-demand rendering |
| **Splat Studio** | No (SHARP model is open-source) | Generated from photos | On-device generation via Apple's SHARP model |
| **i3DGS3D** | No | PLY, SPZ | SBS/anaglyph output, tabbed viewer |
| **AirVis** | No | Captured from iPhone | Capture + view workflow |

**Performance notes:**
- Large PLY files (250MB+) can cause frame drops or crashes
- Release mode (no debugger) recommended for best performance
- MetalSplatter uses Metal amplification for efficient stereo rendering
- Scene complexity is the main bottleneck, not the rendering approach itself

### 4.4 RealityKit Capabilities for Volumetric Rendering

**RealityKit rendering paths on visionOS:**

1. **ShaderGraphMaterial:** Node-based custom surface and geometry shaders. Works in all visionOS modes (shared, mixed, full immersion). Recommended for most cases.

2. **LowLevelMesh + Metal Compute (visionOS 2+):** Custom vertex layouts, GPU-driven updates via compute shaders. Ideal for point clouds, particle systems, dynamic geometry. Can be used within RealityKit's scene graph.

3. **Compositor Services + Full Metal Pipeline:** Complete control over rendering. Required for fully custom rendering (like Gaussian splatting). Works in full and mixed immersive modes (visionOS 2+). Must produce correct pre-multiplied alpha, P3 color space output.

4. **VideoPlayerComponent:** Embed video playback in RealityKit scenes. Supports MV-HEVC for stereo. Best for pre-rendered or cloud-rendered content.

**Key constraints:**
- `CustomMaterial` with Metal shader functions is **iOS only** (not available on visionOS)
- Full custom Metal rendering requires Compositor Services
- Mixed immersion with Metal only available since visionOS 2

### 4.5 Existing 3DGS Viewers for visionOS

The MetalSplatter open-source library is the most mature option:
- GitHub: [scier/MetalSplatter](https://github.com/scier/MetalSplatter)
- Modules: PLYIO (PLY read/write), SplatIO (splat interpretation), MetalSplatter (rendering)
- Supports PLY, SPZ, .splat formats
- Stereo rendering via Metal amplification
- AR mode in visionOS 2+ via Compositor Services

**Source:** [MetalSplatter GitHub](https://github.com/scier/MetalSplatter), [Apple LowLevelMesh Docs](https://developer.apple.com/documentation/realitykit/lowlevelmesh), [metal-spatial-dynamic-mesh](https://github.com/metal-by-example/metal-spatial-dynamic-mesh), [Spatial Fields](https://spatialfields.app/)

---

## 5. Streaming Volumetric Data

### 5.1 Two Fundamental Approaches

#### Approach A: Stream 3D Data, Render on Device

**How it works:** Compressed 3D representations (point clouds, meshes, Gaussians) are streamed to the headset, which renders locally based on user viewpoint.

**Pros:**
- Instant response to head movement (no network round-trip for view changes)
- Works offline once data is cached
- Content sent once for multiple viewers

**Cons:**
- Very high bandwidth: 30-80+ Mbps per subject (compressed), up to 720 Mbps raw
- Requires powerful client GPU
- 3D codecs less mature than 2D video codecs

**Applicable formats:** V-PCC point clouds, Arcturus AVV/OMS meshes, 3D Gaussians (SPZ/SOGS)

#### Approach B: Cloud Render, Stream 2D Video

**How it works:** Server renders the scene for the user's predicted viewpoint, encodes as standard 2D/stereo video (H.265/MV-HEVC), streams via HLS or WebRTC.

**Pros:**
- Very low client compute (just video decode)
- Low bandwidth (5-15 Mbps, standard video)
- Uses mature, hardware-accelerated codecs
- Works on any device with video playback

**Cons:**
- Latency: requires motion-to-photon prediction (~50-200ms round-trip)
- Each user needs dedicated server render resources
- Quality degrades when prediction is wrong (head turns faster than expected)
- Does not scale well to many concurrent viewers

**Real-world implementations:**
- HypeVR demonstrated cloud-rendered volumetric playback on last-gen iPhones
- PresenZ/Immersix demonstrated cinema-quality CGI cloud-rendered on Quest 3
- Nokia's V3C/MIV system leverages existing 2D video coding tools

#### Approach C: Hybrid (Emerging)

**V3: Viewing Volumetric Videos via Streamable 2D Dynamic Gaussians:**
- Encodes dynamic 3D Gaussian attributes as 2D video streams
- Leverages hardware video codecs (H.265) for compression and decoding
- Combines benefits of both approaches: efficient compression with local rendering capability
- Key insight: treat Gaussian attribute maps as video frames

**LapisGS: Layered Progressive 3D Gaussian Splatting:**
- Progressive quality layers that adapt to network conditions
- Dynamic pruning and opacity interpolation for smooth quality transitions
- Up to 50% SSIM improvement over baselines; 318% model size reduction

**StreamLoD-GS: LoD-Structured Gaussian Splatting for Streaming FVV:**
- Hierarchical LOD with octree + anchor representations
- Gaussian dropout for sparse-view robustness
- GMM-based motion partitioning for temporal coherence

### 5.2 Bandwidth Requirements

| Content Type | Raw | Compressed | Codec |
|-------------|-----|------------|-------|
| Point cloud (200K pts/frame, 30fps) | ~720 Mbps | ~8-50 Mbps | V-PCC |
| Textured mesh sequence | ~500+ Mbps | ~20-80 Mbps | AVV/OMS |
| 3D Gaussian scene (static) | N/A (one-time load) | 5-30 MB total | SPZ/SOGS |
| Dynamic 4D Gaussians | TBD | ~10-40 Mbps (est.) | Research stage |
| MIV (multi-view immersive) | ~200+ Mbps | ~25 Mbps | HEVC-based |
| Cloud-rendered stereo video | N/A | 5-15 Mbps | H.265/MV-HEVC |

### 5.3 Bandwidth Reduction Techniques

1. **FoV-adaptive streaming:** Only download content in the user's predicted field of view. Saves 40-60% bandwidth.
2. **3D tiling:** Divide scene into spatial tiles, cull/reduce LOD based on distance and view frustum.
3. **Super-resolution:** Stream low-resolution, upscale on device. VoLUT achieves 30+ fps on mobile with 70% bandwidth reduction.
4. **Progressive loading:** Send base layer first, refine with additional data. SH band progressive loading for Gaussians.
5. **Temporal coherence:** Exploit frame-to-frame similarity. Only send deltas/deformations.
6. **AI-driven prediction:** Predictive encoding based on user behavior patterns.

### 5.4 Level-of-Detail for Gaussian Splatting

Recent research has produced several LOD approaches specifically for streaming 3DGS:

- **A LoD of Gaussians (2025):** Hybrid LOD with Sequential Point Trees. Stores full scene out-of-core, streams only relevant Gaussians. First approach to achieve bounded-memory training/rendering of 60M+ Gaussians on consumer GPUs (24GB VRAM).
- **Virtual Memory for 3DGS (2026):** Leverages virtual memory/texturing techniques to identify visible Gaussians and stream them to GPU just-in-time.
- **LS-Gaussian (2025):** Lightweight streaming framework for resource-constrained platforms. Uses viewpoint transformation for efficient sparse rendering.

**Source:** [LapisGS (arXiv)](https://arxiv.org/html/2408.14823v1), [V3 (arXiv)](https://arxiv.org/html/2409.13648v2), [StreamLoD-GS (arXiv)](https://arxiv.org/html/2601.18475), [Cloud Rendering Volumetric (arXiv)](https://arxiv.org/abs/2003.02526)

---

## 6. Implications for Parallaxis

### 6.1 What's Achievable Today (2024-2026)

**Proven:**
- 3D Gaussian splatting renders in real-time on Vision Pro (MetalSplatter, Spatial Fields)
- Sparse-view (4-12 cameras) reconstruction is possible with modern neural methods
- Pose-free reconstruction from uncalibrated views is an active, rapidly improving research area
- Cloud-rendered volumetric video with view prediction works at scale
- Standard video streaming (HLS + MV-HEVC) to Vision Pro is well-supported

**Emerging (research, not production):**
- Dynamic 4D Gaussian splatting at real-time rates
- Progressive streaming of Gaussian splat scenes
- Feed-forward sparse-view reconstruction without per-scene training
- Encoding Gaussian attributes as standard video streams

**Not yet solved:**
- Real-time dynamic 3DGS from live, sparse, handheld cameras in the wild
- Streaming dynamic Gaussian scenes to headsets at interactive rates
- Graceful quality degradation in sparse-coverage regions of a crowdsourced array

### 6.2 Recommended Architecture Considerations

**Short-term (Phase 1-2):** Cloud-render approach
- Reconstruct scene server-side using multi-view inputs
- Render stereo views for requested viewpoint on server
- Encode as MV-HEVC, stream via LL-HLS or WebRTC
- Pros: Works with existing Vision Pro video pipeline, proven approach
- Cons: Per-user server rendering cost, prediction latency

**Medium-term (Phase 3-4):** Hybrid Gaussian approach
- Reconstruct dynamic 3D Gaussian scene on server
- Stream compressed Gaussian data (V3-style 2D encoding or SPZ-based progressive)
- Render locally on Vision Pro via MetalSplatter-style pipeline
- Pros: Local rendering eliminates prediction latency, better scalability
- Cons: Higher client compute, codec immaturity

**Long-term (Phase 5):** Full local rendering
- Feed-forward sparse-view reconstruction on edge/cloud
- Stream full dynamic Gaussian scene to device
- Full local 6DOF rendering with progressive LOD
- Pros: Best quality, lowest latency, scales to many viewers
- Cons: Depends on research breakthroughs in dynamic streaming

### 6.3 Key Differentiators from Existing Systems

| Existing System | Fixed Cameras | Pre-calibrated | Studio Environment | Parallaxis |
|----------------|---------------|----------------|-------------------|------------|
| Intel True View | 38, permanent | Yes | Stadium (permanent install) | Dynamic, handheld |
| Canon Free Viewpoint | 100+, permanent | Yes | Stadium (permanent install) | Crowdsourced |
| 4DViews HOLOSYS | 32-48, fixed | Yes | Green screen studio | Open venue |
| Microsoft/Arcturus | 100+, fixed | Yes | Portable studio | No studio |

Parallaxis is attempting something fundamentally harder: uncalibrated, dynamic, handheld, sparse, heterogeneous camera inputs in an uncontrolled environment. The closest research analogue is the sparse-view, pose-free Gaussian splatting work (FreeSplatter, MVSplat, InstantSplat), but extending this to dynamic scenes with live video is still an open problem.

### 6.4 Critical Research Gaps for Parallaxis

1. **Live dynamic scene reconstruction from sparse handheld cameras** — 4D Gaussian methods assume static multi-view capture or controlled setups. Adapting to live, moving, crowdsourced inputs is novel.
2. **Real-time global coordinate alignment** — ARKit provides per-device 6DOF, but fusing N devices into a shared coordinate system while they join/leave is unsolved at scale.
3. **Efficient streaming of dynamic volumetric content** — The V3 approach (Gaussians as 2D video) is promising but only demonstrated for pre-captured content.
4. **Graceful degradation** — No existing system handles the extreme heterogeneity (quality, coverage, stability) of crowdsourced inputs.
