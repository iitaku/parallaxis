import SwiftUI
import RealityKit

struct ContentView: View {
    @StateObject private var capture = CaptureManager()
    @State private var serverAddress = ""
    @AppStorage("lastServerAddress") private var savedAddress = ""

    var body: some View {
        ZStack {
            // Camera preview
            ARViewContainer(arView: capture.arView)
                .ignoresSafeArea()

            // Overlay UI
            VStack {
                Spacer()

                // Status panel
                VStack(spacing: 8) {
                    HStack {
                        Circle()
                            .fill(capture.isCapturing ? .green : .gray)
                            .frame(width: 10, height: 10)
                        Text(capture.statusMessage)
                            .font(.caption)
                    }

                    if capture.isCapturing {
                        HStack(spacing: 16) {
                            Label("\(capture.frameCount)", systemImage: "photo")
                            Label(String(format: "%.1f fps", capture.currentFPS), systemImage: "speedometer")
                            if capture.depthAvailable {
                                Label("LiDAR", systemImage: "dot.radiowaves.left.and.right")
                                    .foregroundStyle(.green)
                            }
                        }
                        .font(.caption2)
                    }

                    if !capture.isCapturing {
                        HStack {
                            TextField("Mac IP (e.g. 192.168.1.10)", text: $serverAddress)
                                .textFieldStyle(.roundedBorder)
                                .keyboardType(.decimalPad)
                                .autocorrectionDisabled()
                            Button(action: startCapture) {
                                Image(systemName: "play.fill")
                            }
                            .buttonStyle(.borderedProminent)
                            .disabled(serverAddress.isEmpty)
                        }
                    } else {
                        Button("Stop", systemImage: "stop.fill") {
                            capture.stopCapture()
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(.red)
                    }
                }
                .padding()
                .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
                .padding()
            }
        }
        .onAppear {
            if !savedAddress.isEmpty {
                serverAddress = savedAddress
            }
        }
    }

    private func startCapture() {
        savedAddress = serverAddress
        capture.startCapture(serverAddress: serverAddress)
    }
}

/// UIViewRepresentable wrapper for ARView.
struct ARViewContainer: UIViewRepresentable {
    let arView: ARView

    func makeUIView(context: Context) -> ARView {
        arView
    }

    func updateUIView(_ uiView: ARView, context: Context) {}
}
