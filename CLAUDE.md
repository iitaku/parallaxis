# Parallaxis — Project Brief

## Overview

**Parallaxis** is a personal project to build a system that dynamically composes immersive content from multiple cameras in a single physical space (sports stadiums, concert venues, etc.) and enables free-viewpoint viewing on Apple Vision Pro.

The name derives from the Greek "παράλλαξις" (parallaxis) — meaning change/shift in perspective — evoking a god's-eye view where the viewer can freely choose any vantage point within the venue.

## Core Concept

Audience members at a live event voluntarily contribute their personal iPhones as a distributed, crowdsourced camera array. The system:

1. **Recruits** audience iPhones via a lightweight capture app (join via QR code, deep link, etc.)
2. **Ingests** real-time feeds from dynamically joining/leaving phones across the venue
3. **Calibrates** camera poses on-the-fly from unknown, unstable, handheld positions
4. **Reconstructs** a volumetric/free-viewpoint representation of the scene
5. **Synthesizes** novel views dynamically based on the viewer's chosen perspective
6. **Streams** the result as immersive content to Apple Vision Pro

The end user wearing Vision Pro can "sit" anywhere in the venue, look in any direction, and experience the event as if physically present from that vantage point.

## Core Design Principle: Crowdsourced Capture

Unlike traditional free-viewpoint systems (Intel True View, Canon) that use fixed, pre-calibrated professional camera rigs, Parallaxis embraces the chaos of personal devices:

- **Dynamic topology**: Cameras join and leave at any time. The system must gracefully handle a fluctuating set of contributors.
- **Unknown poses**: No pre-calibration. Camera positions and orientations must be estimated in real-time from visual features and device sensors (ARKit, IMU, GPS/UWB).
- **Heterogeneous quality**: Different iPhone models, varying lens quality, inconsistent exposure/white balance. The system must normalize and fuse heterogeneous inputs.
- **Handheld instability**: Contributors are humans watching an event, not tripods. Expect shake, occlusion (hands, heads), and abrupt movements.
- **Incentive & UX**: Contributors need a reason to participate and the capture app must be near-zero friction — ideally they can still enjoy the event while contributing.
- **Privacy**: Contributors consent to sharing their camera feed. The system must handle this transparently.

## Target Platforms

- **Capture side**: Audience members' personal iPhones (iPhone 15 Pro+ recommended for spatial video / LiDAR / ARKit capabilities)
- **Compute side**: Cloud/edge server for real-time calibration, reconstruction, and view synthesis
- **Playback side**: Apple Vision Pro (visionOS 26+)

## Key Technical Stack & APIs

### visionOS 26 (WWDC25) — Playback

- **Apple Projected Media Profile (APMP)**: New format supporting 180°/360°/Wide FOV video. Playback via QuickLook, AVKit, RealityKit, with HLS support.
- **ImmersiveMediaSupport framework**: New in visionOS 26. Read/write metadata for Apple Immersive Video. Enables custom tools and workflows.
- **AVExperienceController API**: Programmatic transitions from Expanded to Immersive playback.
- **MV-HEVC (Multiview HEVC)**: Apple's stereo video codec. Single track carries left+right eye views. Hardware-accelerated encode/decode on Apple Silicon.
- **Video Extended Usage (VEXU) boxes**: Metadata signaling projection type (equirectangular, half-equirectangular, parametric), stereo mode, view packing.
- **RealityKit VideoPlayerComponent**: Embed video in custom immersive environments.
- **HLS with APMP signaling**: Stream immersive content with updated HLS playlist format.

### Capture & Crowd Coordination (iPhone App)

- **ARKit / ARWorldTrackingConfiguration**: Real-time 6DoF pose estimation (position + orientation) from visual-inertial odometry. Critical for on-the-fly camera calibration without a pre-surveyed rig.
- **AVCaptureSession**: Video capture with intrinsic metadata (focal length, lens distortion).
- **VTCompressionSession**: Hardware H.265/HEVC real-time encoding on Apple Silicon for efficient uplink.
- **CoreMotion (IMU)**: Accelerometer + gyroscope for pose refinement and motion compensation.
- **MultipeerConnectivity / Custom networking**: Device discovery and coordination within the venue.
- **NTP / PTP time sync**: Frame-level synchronization across devices. Leverage NTPClient or server-issued timestamps.
- **UWB (U1/U2 chip)**: Relative positioning between nearby iPhones for spatial anchor bootstrapping.
- **Camera intrinsics via AVCaptureDevice**: Per-model lens parameters for undistortion.
- iPhone 17 Pro capabilities: 4K/60fps HEVC, LiDAR, ARKit world tracking, Spatial Video (1080p/30fps MV-HEVC, ~63° FOV).

### View Synthesis (Research/Implementation Area)

Core reconstruction approaches to evaluate:

- **3D Gaussian Splatting (3DGS)**: Real-time novel view synthesis, fast training, explicit representation. Strong candidate for dynamic scenes.
- **Neural Radiance Fields (NeRF)**: Implicit volumetric representation. Higher quality but slower; dynamic variants (D-NeRF, K-Planes) exist.
- **Multi-plane Images (MPI)**: Layer-based representation, efficient for narrow baseline interpolation.
- **Traditional MVS + point cloud**: Multi-view stereo → dense point cloud → mesh → texture. More mature but less flexible.
- **Depth estimation + warping**: Monocular/stereo depth → image-based rendering. Fastest but lower quality for large viewpoint changes.

### Streaming & Transport

- **HLS (HTTP Live Streaming)**: Standard Apple delivery. CMAF Low-Latency HLS for ~1-2s latency.
- **WebRTC**: Sub-second latency for real-time interactivity.
- **Custom MV-HEVC streaming**: Synthesized stereo views encoded as MV-HEVC and delivered via HLS.

## Architecture (High-Level)

```
┌─────────────────────────────────────────────────┐
│                   VENUE                          │
│                                                  │
│   🪪 QR Code / Deep Link / NFC tap              │
│         "Join this event on Parallaxis"          │
│                                                  │
│   📱 📱 📱 📱 📱    📱 📱 📱 📱 📱             │
│   Audience iPhones (dynamic, handheld)           │
│   - ARKit 6DoF pose tracking                     │
│   - HEVC video stream + pose metadata            │
│   - IMU + UWB relative positioning               │
│                                                  │
└──────────────────┬──────────────────────────────┘
                   │ Uplink per device:
                   │ HEVC stream + pose + intrinsics
                   │ (WebSocket / QUIC / custom)
                   ▼
┌─────────────────────────────────────────────────┐
│              COMPUTE BACKEND                     │
│                                                  │
│  ┌─────────────────────────────────────────────┐│
│  │ Session Coordinator                         ││
│  │ - Device join/leave management              ││
│  │ - Time sync orchestration                   ││
│  │ - Coverage map (which areas are captured)   ││
│  └─────────────────────────────────────────────┘│
│                                                  │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ Real-time   │  │ Scene Reconstruction     │  │
│  │ Calibration │  │ (3DGS / NeRF / MVS)     │  │
│  │ - SfM from  │  │ - Fuse N dynamic feeds   │  │
│  │   ARKit +   │  │ - Handle gaps/occlusion  │  │
│  │   visual    │  │ - Incremental updates    │  │
│  └─────────────┘  └──────────┬───────────────┘  │
│                              │                   │
│  ┌───────────────────────────▼───────────────┐  │
│  │ Novel View Synthesis Engine               │  │
│  │ - Receives viewer pose from Vision Pro    │  │
│  │ - Renders stereo pair for requested view  │  │
│  │ - Encodes as MV-HEVC                      │  │
│  └───────────────────────────┬───────────────┘  │
│                              │                   │
│  ┌───────────────────────────▼───────────────┐  │
│  │ Streaming Server                          │  │
│  │ - HLS (CMAF-LL) or WebRTC                │  │
│  │ - APMP metadata injection                 │  │
│  └───────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────┘
                   │ Immersive stream
                   ▼
┌─────────────────────────────────────────────────┐
│          APPLE VISION PRO                        │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │ Parallaxis visionOS App                   │  │
│  │                                           │  │
│  │ - AVPlayerViewController + Immersive      │  │
│  │ - Head/gaze tracking → pose to backend    │  │
│  │ - Venue map UI for viewpoint selection     │  │
│  │ - Coverage heatmap (where cameras exist)  │  │
│  │ - Smooth viewpoint transition              │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Phased Development Plan

### Phase 1: Foundation & Proof of Concept
- Set up monorepo structure
- Build basic visionOS app that plays MV-HEVC / APMP content via HLS
- Test with static pre-rendered immersive content
- Build minimal iPhone capture app (single camera, ARKit pose, HEVC stream to server)

### Phase 2: Crowdsourced Capture
- Session management: create/join event via QR code or deep link
- Multi-device time synchronization (NTP-based)
- Real-time ARKit pose + camera intrinsics upload alongside video
- Device join/leave handling, contributor UX (minimal friction, can still watch event)
- Coverage map: track which areas of the venue have active cameras

### Phase 3: Real-time Calibration & Reconstruction
- Global coordinate system alignment from per-device ARKit poses
- Cross-device pose refinement using shared visual features (SfM-like)
- Evaluate 3DGS vs NeRF vs traditional MVS for dynamic scenes with unstable, sparse cameras
- Handle gaps, occlusion, and varying quality across heterogeneous devices
- Incremental scene updates as cameras move or join/leave

### Phase 4: View Synthesis & Streaming
- Real-time novel view synthesis from fused multi-camera data
- Stereo pair generation (MV-HEVC) for arbitrary viewpoints
- Viewer pose → backend → synthesized view feedback loop
- Latency optimization (target: <500ms motion-to-photon for viewport changes)
- Adaptive quality: degrade gracefully in sparse-coverage areas

### Phase 5: Production Quality
- Spatial Audio synthesis matching viewpoint
- Coverage-aware UI: show viewer where quality is best/worst
- Smooth viewpoint transitions with interpolation
- Multi-viewer support (many Vision Pro viewers, one event)
- Contributor incentives & social features

## Repository Structure (Proposed)

```
parallaxis/
├── CLAUDE.md               # This file — project context for Claude Code
├── README.md
├── docs/
│   ├── architecture.md
│   ├── research/           # Notes on 3DGS, NeRF, crowd calibration, etc.
│   └── api-reference.md
├── apps/
│   ├── vision-pro/         # visionOS viewer app (Swift/SwiftUI)
│   ├── contributor/        # iPhone capture/contributor app (Swift)
│   └── web-dashboard/      # Event management & monitoring UI
├── server/
│   ├── session/            # Session coordinator (create/join/leave events)
│   ├── ingest/             # Multi-device video ingest service
│   ├── calibration/        # Real-time cross-device pose alignment
│   ├── synthesis/          # View synthesis engine (3DGS/NeRF)
│   ├── streaming/          # HLS/WebRTC output server
│   └── coverage/           # Spatial coverage tracking & heatmap
├── shared/
│   ├── protocols/          # Shared data formats (pose, intrinsics, sync)
│   └── spatial-metadata/   # MV-HEVC / APMP metadata utils
└── scripts/
    ├── setup.sh
    └── dev.sh
```

## Key References

- [WWDC25: Explore video experiences for visionOS](https://developer.apple.com/videos/play/wwdc2025/304/)
- [WWDC25: Learn about Apple Immersive Video technologies](https://developer.apple.com/videos/play/wwdc2025/403/)
- [WWDC25: Support immersive video playback in visionOS apps](https://developer.apple.com/videos/play/wwdc2025/296/)
- [WWDC25: Learn about the Apple Projected Media Profile](https://developer.apple.com/videos/play/wwdc2025/297/)
- [WWDC23: Deliver video content for spatial experiences](https://developer.apple.com/videos/play/wwdc2023/10071/)
- [WWDC24: Build compelling spatial photo and video experiences](https://developer.apple.com/videos/play/wwdc2024/10166/)
- [SpatialPlayer (GitHub)](https://github.com/mikeswanson/SpatialPlayer) — MV-HEVC player example
- [awesome-visionOS (GitHub)](https://github.com/tomkrikorian/awesome-visionOS) — Resource collection
- [Apple HEVC Stereo Video Interoperability Profile](https://developer.apple.com/documentation/) — MV-HEVC spec
- [Spatial Video Streaming on Vision Pro (HotMobile '25)](https://dl.acm.org/doi/10.1145/3708468.3711878) — Research paper on SVS challenges
- [OpenImmersive / WWDC25 Deep Dive](https://medium.com/@portemantho/wwdc-25-deep-dive-immersive-video-openimmersive-1-4-3f7fe6054e96) — Practical analysis of visionOS 26 video APIs
- [Apple Immersive Video Utility](https://support.apple.com/guide/immersive-video-utility/) — Real-time camera streaming to Vision Pro
- [Voodoo Spatial](https://apps.apple.com/us/app/voodoo-spatial/id6497950663) — Existing spatial video streaming app (reference)
- [Converting SBS 3D to MV-HEVC (Apple docs)](https://developer.apple.com/documentation/AVFoundation/converting-side-by-side-3d-video-to-multiview-hevc-and-spatial-video)

## Existing Solutions & Competitive Landscape

- **Voodoo Spatial**: iPhone → Vision Pro spatial video livestreaming. Single camera, no free viewpoint.
- **Apple Immersive Video Utility**: Mac-connected immersive camera preview on Vision Pro. Production workflow tool, not consumer.
- **Intel True View / Canon Free Viewpoint**: Stadium-scale multi-camera free viewpoint for broadcast. Proprietary, not Vision Pro native.
- **Blackmagic URSA Cine Immersive**: $30K camera for Apple Immersive Video. Single camera, fixed viewpoint.

**Parallaxis differentiator**: Crowdsourced audience iPhones → real-time volumetric reconstruction → free-viewpoint immersive streaming natively to Vision Pro. No dedicated camera infrastructure required — the audience IS the camera array.

## Key Technical Challenges (Crowdsourced Model)

1. **Dynamic calibration**: ARKit gives per-device 6DoF, but aligning N devices into a shared global coordinate system in real-time — with devices joining/leaving — is an open research problem. Visual overlap between devices, shared landmark detection, or UWB ranging can help.

2. **Sparse & irregular coverage**: Unlike a pre-planned camera rig, audience cameras cluster in certain areas (stands, pit) and leave gaps. The system must gracefully degrade in sparse regions rather than fail.

3. **Uplink bandwidth**: Each contributor streaming HEVC over venue WiFi/cellular. With 50-200+ contributors, aggregate uplink becomes a bottleneck. Need adaptive bitrate per contributor, selective frame/region upload, or edge aggregation.

4. **Contributor UX**: People came to enjoy the event, not operate a camera. The app must work with minimal interaction — ideally "open app, tap join, put phone in pocket or hold naturally." Consider using rear camera while user watches with their eyes.

5. **Synchronization**: Frame-accurate sync across N consumer devices with varying network latency. NTP + device-local timestamps + server-side alignment.

6. **Robustness**: Expect dropped connections, occluded lenses, wildly shaking devices, fingers over cameras, portrait/landscape mix. The pipeline must be fault-tolerant.
