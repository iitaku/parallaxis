# ParallaxisCapture — iPhone Depth Streaming Prototype

iPhone の ARKit (LiDAR) で取得した RGB + 深度 + カメラ姿勢を Mac にリアルタイムストリーミングするプロトタイプ。

## アーキテクチャ

```
iPhone (LiDAR)              Mac
┌────────────────┐    WiFi   ┌──────────────────┐
│ ARKit          │ ────────→ │ receiver.py      │
│  RGB (JPEG)    │  WebSocket│  RGB 表示         │
│  Depth (F32)   │  :8765    │  Depth 可視化     │
│  Pose (4x4)    │           │  フレーム保存     │
│  Intrinsics    │           │                  │
└────────────────┘           └──────────────────┘
```

## 必要なもの

### iPhone 側
- iPhone 12 Pro 以降（LiDAR 搭載モデル）
- iOS 17+
- Xcode 16+ (ビルド用)

### Mac 側
- Python 3.10+
- 同じ WiFi ネットワーク上にあること

## セットアップ

### 1. Mac レシーバの起動

```bash
cd server/ingest
pip install -r requirements.txt
python receiver.py
```

起動すると Mac の IP アドレスが表示される:
```
=== Parallaxis Receiver ===
  Listening on 0.0.0.0:8765
  Local IP: 192.168.1.10
  Enter '192.168.1.10' in the iPhone app to connect
```

### 2. iPhone アプリのビルド

Xcode で新規プロジェクトを作成:

1. **File → New → Project → iOS → App**
2. Product Name: `ParallaxisCapture`
3. Interface: **SwiftUI**
4. Language: **Swift**
5. プロジェクト作成後、デフォルトのソースファイルを削除
6. `ParallaxisCapture/` 内の4つの .swift ファイルをプロジェクトに追加:
   - `ParallaxisCaptureApp.swift`
   - `ContentView.swift`
   - `CaptureManager.swift`
   - `FrameStreamer.swift`

**Info.plist に以下を追加** (Target → Info → Custom iOS Target Properties):

| Key | Value |
|-----|-------|
| `NSCameraUsageDescription` | ARKit depth capture for Parallaxis |
| `NSLocalNetworkUsageDescription` | Stream depth data to Mac receiver |

**Signing**: 自分の Apple Developer アカウントで署名

7. iPhone を接続して **Run** (実機のみ、シミュレータでは ARKit 不可)

### 3. 接続

1. iPhone アプリに Mac の IP アドレスを入力 (レシーバ起動時に表示されたもの)
2. **▶** ボタンをタップ
3. Mac 側に OpenCV ウィンドウが表示され、RGB と深度マップがリアルタイムで可視化される

## コマンドラインオプション (Mac レシーバ)

```bash
# 基本起動
python receiver.py

# フレームをディスクに保存
python receiver.py --save

# 保存先を指定
python receiver.py --save --output-dir ./my_capture

# ポート変更
python receiver.py --port 9000

# ヘッドレスモード (表示なし、保存のみ)
python receiver.py --save --no-display
```

## 通信プロトコル

各フレームは WebSocket で3メッセージとして送信:

1. **Text**: JSON メタデータ
```json
{
  "type": "frame",
  "frameNumber": 42,
  "timestamp": 1234567890.123,
  "pose": [/* 4x4 column-major, 16 floats */],
  "intrinsics": [/* 3x3 column-major, 9 floats */],
  "depthWidth": 256,
  "depthHeight": 192,
  "rgbWidth": 1920,
  "rgbHeight": 1440
}
```
2. **Binary**: Depth map (Float32, row-major, 256×192×4 = 196,608 bytes)
3. **Binary**: RGB (JPEG, ~50-150 KB)

## 保存されるデータ

`--save` 指定時、`data/stream/` に以下が保存される:

```
data/stream/
  rgb/000001.jpg        # JPEG 画像
  depth/000001.npy      # NumPy float32 配列 (256×192)
  meta/000001.json      # カメラ姿勢・内部パラメータ
```

このデータは後の DIBR ステレオ合成や 3DGS 学習に直接利用可能。

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| "LiDAR not available" | iPhone 12 Pro 以降が必要。SE/mini は LiDAR なし |
| 接続できない | 同じ WiFi か確認。Mac のファイアウォールでポート 8765 を許可 |
| フレームレートが低い | WiFi 帯域を確認。5GHz 帯推奨 |
| Depth が空 | ARKit の初期化に数秒かかる。少し待つ |

## 次のステップ

このプロトタイプで取得したデータを使って:

1. **DIBR ステレオ合成**: RGB + Depth → 左右眼画像 → MV-HEVC 空間動画
2. **既存パイプラインとの統合**: 保存データを `pipeline/` で 3DGS 学習に利用
3. **リアルタイム化**: Mac 上で DIBR + MV-HEVC エンコード → Vision Pro ストリーム
