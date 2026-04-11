#!/usr/bin/env python3
"""
Parallaxis — Mac Receiver

WebSocket server that receives RGB + Depth + Pose frames from the iPhone
capture app and displays them with OpenCV.

Usage:
    python receiver.py                        # listen on 0.0.0.0:8765, visualize
    python receiver.py --save                 # also save frames to disk
    python receiver.py --port 9000            # custom port
    python receiver.py --no-display           # headless (save only)

Protocol (per frame, 3 WebSocket messages):
    1. Text:   JSON metadata (pose, intrinsics, dimensions, timestamp)
    2. Binary: Depth map (Float32, row-major, depthWidth * depthHeight * 4 bytes)
    3. Binary: RGB image (JPEG compressed)
"""

import argparse
import asyncio
import json
import signal
import struct
import sys
import time
from pathlib import Path

import cv2
import numpy as np

try:
    import websockets
    from websockets.asyncio.server import serve
except ImportError:
    print("Missing dependency. Install with: pip install websockets")
    sys.exit(1)


class FrameStats:
    """Track receive statistics."""

    def __init__(self):
        self.frame_count = 0
        self.start_time = time.time()
        self.last_print_time = time.time()
        self.last_print_count = 0
        self.total_rgb_bytes = 0
        self.total_depth_bytes = 0

    def update(self, rgb_bytes: int, depth_bytes: int):
        self.frame_count += 1
        self.total_rgb_bytes += rgb_bytes
        self.total_depth_bytes += depth_bytes

    def fps(self) -> float:
        now = time.time()
        elapsed = now - self.last_print_time
        if elapsed < 1.0:
            return 0.0
        fps = (self.frame_count - self.last_print_count) / elapsed
        self.last_print_count = self.frame_count
        self.last_print_time = now
        return fps


class Receiver:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.stats = FrameStats()
        self.latest_display = None  # BGR image for OpenCV display
        self.save_dir = None
        if args.save:
            self.save_dir = Path(args.output_dir)
            self.save_dir.mkdir(parents=True, exist_ok=True)
            (self.save_dir / "rgb").mkdir(exist_ok=True)
            (self.save_dir / "depth").mkdir(exist_ok=True)
            (self.save_dir / "meta").mkdir(exist_ok=True)

    async def handle_client(self, websocket):
        """Handle one connected iPhone client."""
        addr = websocket.remote_address
        print(f"[+] iPhone connected from {addr}")

        try:
            while True:
                # 1) JSON metadata (text message)
                raw = await websocket.recv()
                if isinstance(raw, bytes):
                    print("[!] Expected text metadata, got binary. Skipping.")
                    continue
                metadata = json.loads(raw)

                # 2) Depth (binary message)
                depth_bytes = await websocket.recv()
                if not isinstance(depth_bytes, bytes):
                    print("[!] Expected binary depth, got text. Skipping.")
                    continue

                # 3) RGB JPEG (binary message)
                rgb_bytes = await websocket.recv()
                if not isinstance(rgb_bytes, bytes):
                    print("[!] Expected binary RGB, got text. Skipping.")
                    continue

                self.process_frame(metadata, depth_bytes, rgb_bytes)

        except websockets.exceptions.ConnectionClosed:
            print(f"[-] iPhone disconnected ({addr})")

    def process_frame(self, metadata: dict, depth_bytes: bytes, rgb_bytes: bytes):
        """Decode, visualize, and optionally save a received frame."""
        frame_num = metadata.get("frameNumber", 0)
        depth_w = metadata.get("depthWidth", 0)
        depth_h = metadata.get("depthHeight", 0)

        # Decode RGB
        rgb_arr = np.frombuffer(rgb_bytes, dtype=np.uint8)
        rgb = cv2.imdecode(rgb_arr, cv2.IMREAD_COLOR)
        if rgb is None:
            print(f"[!] Frame {frame_num}: failed to decode JPEG")
            return

        # Decode depth
        depth = None
        if depth_w > 0 and depth_h > 0 and len(depth_bytes) > 0:
            expected = depth_w * depth_h * 4  # Float32
            if len(depth_bytes) == expected:
                depth = np.frombuffer(depth_bytes, dtype=np.float32).reshape(depth_h, depth_w)
            else:
                print(f"[!] Frame {frame_num}: depth size mismatch "
                      f"(got {len(depth_bytes)}, expected {expected})")

        # Extract pose position for display
        pose = metadata.get("pose", [])
        pos_str = ""
        if len(pose) == 16:
            # Column-major 4x4 → translation is columns[3] = indices 12,13,14
            tx, ty, tz = pose[12], pose[13], pose[14]
            pos_str = f"pos=({tx:.2f}, {ty:.2f}, {tz:.2f})"

        # Update stats
        self.stats.update(len(rgb_bytes), len(depth_bytes))
        fps = self.stats.fps()
        if fps > 0:
            rgb_rate = self.stats.total_rgb_bytes / (time.time() - self.stats.start_time) / 1e6
            print(f"  Frame {frame_num:5d} | {fps:.1f} fps | "
                  f"RGB {len(rgb_bytes)/1024:.0f}KB | "
                  f"Depth {len(depth_bytes)/1024:.0f}KB | "
                  f"{pos_str} | "
                  f"Total {rgb_rate:.1f} MB/s")

        # Build display image
        if not self.args.no_display:
            self.latest_display = self.build_display(rgb, depth, metadata)

        # Save to disk
        if self.save_dir is not None:
            self.save_frame(frame_num, metadata, depth, rgb_bytes)

    def build_display(self, rgb: np.ndarray, depth: np.ndarray | None,
                      metadata: dict) -> np.ndarray:
        """Build a side-by-side RGB + colorized depth image for display."""
        display_h = 480
        # Resize RGB
        h, w = rgb.shape[:2]
        scale = display_h / h
        rgb_small = cv2.resize(rgb, (int(w * scale), display_h))

        if depth is not None:
            # Colorize depth: clip to 0-5m, normalize to 0-255, apply colormap
            depth_clipped = np.clip(depth, 0.0, 5.0)
            depth_norm = (depth_clipped / 5.0 * 255).astype(np.uint8)
            depth_color = cv2.applyColorMap(depth_norm, cv2.COLORMAP_TURBO)
            # Resize to match RGB height
            dh, dw = depth_color.shape[:2]
            depth_scale = display_h / dh
            depth_small = cv2.resize(depth_color, (int(dw * depth_scale), display_h))
            display = np.hstack([rgb_small, depth_small])
        else:
            # No depth: show placeholder
            placeholder = np.zeros((display_h, 200, 3), dtype=np.uint8)
            cv2.putText(placeholder, "No Depth", (20, display_h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 128, 128), 2)
            display = np.hstack([rgb_small, placeholder])

        # Overlay text
        frame_num = metadata.get("frameNumber", 0)
        cv2.putText(display, f"Frame: {frame_num}  "
                    f"Received: {self.stats.frame_count}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        return display

    def save_frame(self, frame_num: int, metadata: dict,
                   depth: np.ndarray | None, rgb_bytes: bytes):
        """Save frame data to disk."""
        prefix = f"{frame_num:06d}"
        # JPEG as-is
        (self.save_dir / "rgb" / f"{prefix}.jpg").write_bytes(rgb_bytes)
        # Depth as .npy
        if depth is not None:
            np.save(self.save_dir / "depth" / f"{prefix}.npy", depth)
        # Metadata as JSON
        with open(self.save_dir / "meta" / f"{prefix}.json", "w") as f:
            json.dump(metadata, f, indent=2)


async def main():
    parser = argparse.ArgumentParser(description="Parallaxis Mac Receiver")
    parser.add_argument("--port", type=int, default=8765,
                        help="WebSocket port (default: 8765)")
    parser.add_argument("--save", action="store_true",
                        help="Save received frames to disk")
    parser.add_argument("--output-dir", default="data/stream",
                        help="Output directory for saved frames (default: data/stream)")
    parser.add_argument("--no-display", action="store_true",
                        help="Disable OpenCV visualization window")
    args = parser.parse_args()

    receiver = Receiver(args)

    # Print local IP addresses for easy connection
    import socket
    hostname = socket.gethostname()
    try:
        # Get LAN IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "unknown"

    print(f"=== Parallaxis Receiver ===")
    print(f"  Listening on 0.0.0.0:{args.port}")
    print(f"  Local IP: {local_ip}")
    print(f"  Enter '{local_ip}' in the iPhone app to connect")
    print(f"  Save: {'ON → ' + args.output_dir if args.save else 'OFF'}")
    print(f"  Display: {'OFF' if args.no_display else 'ON'}")
    print(f"  Press Ctrl+C to stop")
    print()

    # Start WebSocket server
    async with serve(receiver.handle_client, "0.0.0.0", args.port) as server:
        # If display is enabled, run OpenCV window in a loop
        if not args.no_display:
            print("  OpenCV window will appear when the first frame arrives.")
            while True:
                if receiver.latest_display is not None:
                    cv2.imshow("Parallaxis Receiver", receiver.latest_display)
                key = cv2.waitKey(30) & 0xFF
                if key == ord("q"):
                    print("\n[q] pressed, shutting down.")
                    break
                await asyncio.sleep(0.01)
            cv2.destroyAllWindows()
        else:
            # Headless: just wait
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop.set)
            await stop.wait()


if __name__ == "__main__":
    asyncio.run(main())
