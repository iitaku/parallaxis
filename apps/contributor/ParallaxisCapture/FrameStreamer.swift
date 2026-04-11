import Foundation

/// WebSocket client that streams ARKit frame data to the Mac receiver.
/// Uses actor isolation to safely drop frames when the previous send is still in flight.
actor FrameStreamer {
    private var webSocketTask: URLSessionWebSocketTask?
    private var isSending = false
    private var isConnected = false

    func connect(to host: String, port: Int = 8765) {
        disconnect()
        let url = URL(string: "ws://\(host):\(port)")!
        webSocketTask = URLSession.shared.webSocketTask(with: url)
        webSocketTask?.resume()
        isConnected = true
    }

    func disconnect() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        isConnected = false
        isSending = false
    }

    /// Send a single frame (metadata JSON + depth binary + RGB JPEG binary).
    /// Drops the frame if a previous send is still in progress.
    /// Returns true if the frame was sent, false if dropped.
    @discardableResult
    func sendFrame(metadata: String, depth: Data, rgb: Data) async -> Bool {
        guard isConnected, !isSending else { return false }
        isSending = true
        defer { isSending = false }

        do {
            try await webSocketTask?.send(.string(metadata))
            try await webSocketTask?.send(.data(depth))
            try await webSocketTask?.send(.data(rgb))
            return true
        } catch {
            print("[FrameStreamer] send error: \(error.localizedDescription)")
            return false
        }
    }

    var connected: Bool { isConnected }
}
