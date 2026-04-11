import ARKit
import RealityKit
import CoreImage
import Combine

/// Manages ARKit session, extracts RGB + Depth + Pose, and streams to Mac.
class CaptureManager: NSObject, ObservableObject {
    // MARK: - Published state
    @Published var isCapturing = false
    @Published var frameCount = 0
    @Published var currentFPS: Double = 0
    @Published var depthAvailable = false
    @Published var statusMessage = "Ready"

    // MARK: - AR
    let arView = ARView(frame: .zero, cameraMode: .ar, automaticallyConfigureSession: false)

    // MARK: - Streaming
    let streamer = FrameStreamer()

    // MARK: - Private
    private let ciContext = CIContext()
    private var lastSendTime: TimeInterval = 0
    private let targetInterval: TimeInterval = 1.0 / 15.0  // 15 fps (matches LiDAR rate)
    private var fpsFrameCount = 0
    private var fpsTimer: TimeInterval = 0

    // MARK: - Lifecycle

    func startCapture(serverAddress: String) {
        guard !isCapturing else { return }

        // Connect to Mac receiver
        Task { await streamer.connect(to: serverAddress) }

        // Configure ARKit
        let config = ARWorldTrackingConfiguration()
        if ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth) {
            config.frameSemantics = .sceneDepth
            depthAvailable = true
        } else {
            statusMessage = "Warning: LiDAR not available, depth will be empty"
        }

        arView.session.delegate = self
        arView.session.run(config)
        isCapturing = true
        statusMessage = "Capturing..."
    }

    func stopCapture() {
        arView.session.pause()
        Task { await streamer.disconnect() }
        isCapturing = false
        frameCount = 0
        currentFPS = 0
        statusMessage = "Stopped"
    }
}

// MARK: - ARSessionDelegate

extension CaptureManager: ARSessionDelegate {
    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        // Throttle to target FPS
        let now = frame.timestamp
        guard now - lastSendTime >= targetInterval else { return }
        lastSendTime = now

        // Update FPS counter
        fpsFrameCount += 1
        if now - fpsTimer >= 1.0 {
            let fps = Double(fpsFrameCount) / (now - fpsTimer)
            DispatchQueue.main.async { self.currentFPS = fps }
            fpsFrameCount = 0
            fpsTimer = now
        }

        // Process and send on background task
        let capturedImage = frame.capturedImage
        let depthMap = frame.sceneDepth?.depthMap
        let pose = frame.camera.transform
        let intrinsics = frame.camera.intrinsics
        let frameNum = frameCount

        Task.detached(priority: .userInitiated) { [weak self] in
            guard let self else { return }
            await self.processAndSend(
                capturedImage: capturedImage,
                depthMap: depthMap,
                pose: pose,
                intrinsics: intrinsics,
                timestamp: now,
                frameNumber: frameNum
            )
        }
    }

    // MARK: - Frame processing

    private func processAndSend(
        capturedImage: CVPixelBuffer,
        depthMap: CVPixelBuffer?,
        pose: simd_float4x4,
        intrinsics: simd_float3x3,
        timestamp: TimeInterval,
        frameNumber: Int
    ) async {
        // RGB → JPEG
        let ciImage = CIImage(cvPixelBuffer: capturedImage)
        guard let jpegData = ciContext.jpegRepresentation(
            of: ciImage,
            colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!,
            options: [kCGImageDestinationLossyCompressionQuality as CIImageRepresentationOption: 0.8]
        ) else { return }

        // Depth → raw Float32 bytes
        var depthData = Data()
        var depthWidth = 0
        var depthHeight = 0
        if let depthMap {
            CVPixelBufferLockBaseAddress(depthMap, .readOnly)
            depthWidth = CVPixelBufferGetWidth(depthMap)
            depthHeight = CVPixelBufferGetHeight(depthMap)
            if let base = CVPixelBufferGetBaseAddress(depthMap) {
                depthData = Data(bytes: base, count: depthWidth * depthHeight * MemoryLayout<Float32>.size)
            }
            CVPixelBufferUnlockBaseAddress(depthMap, .readOnly)
        }

        // Build metadata JSON
        let metadata: [String: Any] = [
            "type": "frame",
            "frameNumber": frameNumber,
            "timestamp": timestamp,
            "pose": simdToArray(pose),
            "intrinsics": intrinsicsToArray(intrinsics),
            "depthWidth": depthWidth,
            "depthHeight": depthHeight,
            "rgbWidth": CVPixelBufferGetWidth(capturedImage),
            "rgbHeight": CVPixelBufferGetHeight(capturedImage),
        ]
        guard let jsonData = try? JSONSerialization.data(withJSONObject: metadata),
              let jsonString = String(data: jsonData, encoding: .utf8) else { return }

        // Send
        let sent = await streamer.sendFrame(metadata: jsonString, depth: depthData, rgb: jpegData)
        if sent {
            DispatchQueue.main.async { self.frameCount += 1 }
        }
    }

    // MARK: - Helpers

    /// Convert simd_float4x4 to column-major [Float] array (16 elements).
    private func simdToArray(_ m: simd_float4x4) -> [Float] {
        [m.columns.0.x, m.columns.0.y, m.columns.0.z, m.columns.0.w,
         m.columns.1.x, m.columns.1.y, m.columns.1.z, m.columns.1.w,
         m.columns.2.x, m.columns.2.y, m.columns.2.z, m.columns.2.w,
         m.columns.3.x, m.columns.3.y, m.columns.3.z, m.columns.3.w]
    }

    /// Convert simd_float3x3 to column-major [Float] array (9 elements).
    private func intrinsicsToArray(_ m: simd_float3x3) -> [Float] {
        [m.columns.0.x, m.columns.0.y, m.columns.0.z,
         m.columns.1.x, m.columns.1.y, m.columns.1.z,
         m.columns.2.x, m.columns.2.y, m.columns.2.z]
    }
}
