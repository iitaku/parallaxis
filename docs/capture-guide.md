# iPhone 撮影ガイド — Parallaxis Phase 1

iPhone で撮影した多視点写真から 3DGS 再構成パイプラインを実行するための手順書。

---

## 前提条件

### ハードウェア
- **撮影**: iPhone（モデル不問。iPhone 12 以降推奨）
- **パイプライン実行**: NVIDIA GPU 搭載 PC（RTX 3070+ / VRAM 7GB 以上）、または Apple Silicon Mac（OpenSplat 使用時）
- **MV-HEVC エンコード**: Apple Silicon Mac（macOS 14 Sonoma 以上）
- **検証**: Apple Vision Pro

### ソフトウェア（パイプライン実行マシン）
```bash
# Python 環境
python -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt

# COLMAP（SfM）
# macOS:
brew install colmap
# Linux: https://colmap.github.io/install.html

# spatial CLI（MV-HEVC エンコード、macOS のみ）
brew install spatial

# FFmpeg（空間動画出力時のみ）
brew install ffmpeg
```

---

## Step 1: 撮影

### 被写体の選び方

フェーズごとに難易度を上げていく:

| フェーズ | 被写体 | 難易度 | 目的 |
|---------|--------|--------|------|
| **1a** | テーブル上のオブジェクト（フィギュア、植物、マグカップ等） | 低 | パイプライン動作確認 |
| **1b** | 室内空間（部屋の一角、デスク周り） | 中 | より大きなシーンでの品質評価 |
| **1c** | 屋外の小規模な空間（ベンチ、庭） | 高 | 最終目標（会場スケール）への第一歩 |

### 撮影手順

#### 基本設定
1. iPhone のカメラアプリを起動
2. **写真モード**を使用（ビデオではなく静止画）
3. 設定の確認:
   - `設定 > カメラ > フォーマット` → **高効率**（HEIF）または**互換性優先**（JPEG）、どちらでもよい
   - フラッシュ OFF
   - HDR は ON のまま（デフォルト）でよい
   - Live Photos は OFF 推奨（ファイルサイズ削減のため）

#### 撮影テクニック

**テーブル上のオブジェクトの場合:**

```
        📱 📱 📱 📱 📱        ← 上段（斜め上から）
       /                \
      📱                📱
     /    ┌──────────┐    \
    📱    │  被写体  │    📱   ← 中段（水平）
     \    └──────────┘    /
      📱                📱
       \                /
        📱 📱 📱 📱 📱        ← 下段（少し下から）
```

1. 被写体の周囲を**一周**しながら撮影（約 15-20 枚）
2. 高さを変えてもう一周（斜め上から 10-15 枚）
3. 必要に応じて低い位置からも（5-10 枚）
4. **合計 30-50 枚**が目安

**室内の場合:**

```
    ┌─────────────────────────┐
    │         部屋            │
    │                         │
    │    📱→  📱→  📱→       │  ← 壁際を移動しながら
    │                         │
    │    📱→  📱→  📱→       │  ← 中央付近でも
    │                         │
    │    📱→  📱→  📱→       │  ← 反対側の壁際
    └─────────────────────────┘
```

1. 部屋の各コーナーから中央を向いて撮影
2. 壁に沿って移動しながら、1-2 歩ごとに撮影
3. 高さや角度を変えたバリエーションも入れる
4. **合計 40-50 枚**が目安

### 撮影のポイント（重要）

#### やるべきこと
- **隣の写真と 60-80% オーバーラップ**させる（最重要。一歩動いたら一枚）
- **被写体を様々な角度から**カバーする
- **手ブレを抑える** — しっかり構えてからシャッターを切る
- **全周カバー** — 被写体の「裏側」も忘れずに撮る
- **解像度はフル**のまま（クロップしない）

#### やってはいけないこと
- **大きく移動して撮らない** — 1-2 歩ずつ、少しずつ移動する
- **ズームしない** — 1x（広角レンズ）固定で統一する
- **動く被写体を入れない** — 人や動物が写真間で位置が変わると再構成が失敗する
- **指でレンズを覆わない** — 意外と多いミス
- **露出を大きく変えない** — 明るい窓と暗い室内を交互に撮ると品質が下がる

#### COLMAP が苦手なもの（避けるか、多めに撮る）
- 鏡・ガラス・金属反射面 — 特徴点が安定しない
- 真っ白な壁・均一なタイル — テクスチャがなく特徴点が取れない
- 透明な物体 — ガラス瓶、水等
- 空（大部分が空のカットが多いと失敗しやすい）

---

## Step 2: 写真の転送

iPhone から作業マシンに写真を転送する。

### AirDrop（Mac → Mac の場合、最も手軽）
1. iPhone の写真アプリで撮影した写真を全選択
2. 共有 → AirDrop → 作業マシン
3. 受信した写真を所定のディレクトリに移動

### Image Capture（Mac に USB 接続）
1. iPhone を Lightning/USB-C ケーブルで Mac に接続
2. Mac のイメージキャプチャ.app (`/Applications/Image Capture.app`) を起動
3. 該当の写真を選択 → 読み込み先を指定してダウンロード

### ファイルアプリ経由（Windows/Linux）
1. iPhone → PC を USB 接続
2. iPhone を写真転送デバイスとしてマウント
3. `DCIM/` フォルダから該当の写真をコピー

### 転送後のディレクトリ配置

```bash
# プロジェクトルートに移動
cd /path/to/parallaxis

# シーン用ディレクトリを作成
mkdir -p data/scenes/my_scene/images

# 写真を配置（例: AirDrop で ~/Downloads に受信した場合）
cp ~/Downloads/IMG_*.{HEIC,JPG,jpg,heic} data/scenes/my_scene/images/

# 確認
ls data/scenes/my_scene/images/ | head
# IMG_0001.HEIC
# IMG_0002.HEIC
# ...

ls data/scenes/my_scene/images/ | wc -l
# 35  ← 20枚以上あればOK
```

**注意**: HEIF (.heic) でも JPEG (.jpg) でもパイプラインはどちらも受け付ける。混在も可。

---

## Step 3: パイプライン実行

### フルパイプライン（推奨: 初回はこれで）

```bash
cd /path/to/parallaxis

# 仮想環境の有効化
source .venv/bin/activate

# 全ステップ実行
python -m pipeline --scene my_scene
```

処理内容と所要時間の目安（35 枚、RTX 4090 の場合）:
```
Step 1: COLMAP SfM         — 5-15 分
Step 2: gsplat training    — 15-30 分（30K ステップ）
Step 3: stereo rendering   — 数秒
Step 4: MV-HEVC encoding   — 数秒（macOS のみ）
```

### ステップごとに実行

問題の切り分けや、パラメータ調整時に便利:

```bash
# Step 1 のみ: COLMAP で姿勢推定
python -m pipeline --scene my_scene --steps sfm

# Step 2 のみ: 3DGS 学習
python -m pipeline --scene my_scene --steps train

# Step 3-4: 視点を指定してレンダリング＋エンコード
python -m pipeline --scene my_scene --steps render,encode \
    --position 0.5,0.3,1.5 --look-at 0,0,0
```

### 主要なオプション

```bash
# SfM バックエンドを変更（GLOMAP は COLMAP より 10-100 倍高速）
python -m pipeline --scene my_scene --sfm-tool glomap

# Mac のみ（NVIDIA GPU なし）の場合
python -m pipeline --scene my_scene --backend opensplat --steps sfm,train

# 学習ステップ数を変更（少ない=速いが品質低、多い=遅いが品質高）
python -m pipeline --scene my_scene --training-steps 7000   # 速い、テスト用
python -m pipeline --scene my_scene --training-steps 30000  # デフォルト
python -m pipeline --scene my_scene --training-steps 50000  # 高品質

# レンダリング解像度を変更
python -m pipeline --scene my_scene --steps render,encode --width 1920 --height 1080

# 焦点距離（=画角）を変更
python -m pipeline --scene my_scene --steps render,encode --fx 1800  # 狭い画角 (~60°)
python -m pipeline --scene my_scene --steps render,encode --fx 1200  # デフォルト (~80°)
python -m pipeline --scene my_scene --steps render,encode --fx 800   # 広い画角 (~100°)

# 複数台の iPhone で撮影した場合（カメラ内部パラメータが異なる）
python -m pipeline --scene my_scene --multi-camera

# 空間動画として出力（軌道カメラパス、60 フレーム）
python -m pipeline --scene my_scene --steps render,encode \
    --camera-path orbit --num-frames 60 --output-format video
```

---

## Step 4: 視点の選び方

レンダリングステップでは、3DGS シーン内の任意の位置にバーチャルカメラを配置してステレオペアを生成する。

### 座標系について

COLMAP の出力座標系は**任意スケール**。メートル単位ではない。

視点を決めるには、まず COLMAP が推定した学習カメラの位置を確認する:

```bash
# COLMAP のカメラ位置を確認（簡易的に）
python -c "
import numpy as np
from pathlib import Path
import struct

# images.bin からカメラ位置を読む簡易スクリプト
# 詳細: https://colmap.github.io/format.html
images_bin = Path('data/colmap/my_scene/sparse/0/images.bin')
with open(images_bin, 'rb') as f:
    n = struct.unpack('<Q', f.read(8))[0]
    print(f'Registered cameras: {n}')
    for _ in range(min(n, 5)):
        image_id = struct.unpack('<I', f.read(4))[0]
        qw, qx, qy, qz = struct.unpack('<4d', f.read(32))
        tx, ty, tz = struct.unpack('<3d', f.read(24))
        camera_id = struct.unpack('<I', f.read(4))[0]
        name = b''
        while True:
            c = f.read(1)
            if c == b'\x00': break
            name += c
        n_pts = struct.unpack('<Q', f.read(8))[0]
        f.read(n_pts * 24)  # skip point2D entries
        print(f'  {name.decode()}: pos=({tx:.2f}, {ty:.2f}, {tz:.2f})')
"
```

### 推奨: 学習カメラの近くから始める

学習データに含まれるカメラ位置の**近く**からレンダリングすると品質が高い。離れるほどアーティファクトが増える。

```bash
# 例: カメラが (0.5, 0.3, 1.5) 付近に集中していた場合
# その近くから、被写体の中心 (0, 0, 0) を向いてレンダリング
python -m pipeline --scene my_scene --steps render,encode \
    --position 0.5,0.3,1.5 --look-at 0,0,0

# 少し移動した位置から（品質確認）
python -m pipeline --scene my_scene --steps render,encode \
    --position 0.8,0.3,1.2 --look-at 0,0,0

# 学習カメラから大きく離れた位置（品質が下がる可能性あり）
python -m pipeline --scene my_scene --steps render,encode \
    --position 2.0,1.0,0.0 --look-at 0,0,0
```

---

## Step 5: Vision Pro で確認

### 空間写真の場合
1. 出力ファイル `data/output/my_scene/spatial_photo.heic` を **AirDrop** で Vision Pro に送信
2. Vision Pro の**写真アプリ**で開く
3. 「空間」バッジが表示され、ステレオ表示になることを確認

### 空間動画の場合
1. 出力ファイル `data/output/my_scene/spatial_video.mov` を AirDrop で送信
2. 写真アプリまたは TV アプリで再生
3. 空間動画として立体表示になることを確認

### チェックポイント

| 項目 | 確認内容 | 問題があった場合 |
|------|---------|----------------|
| **ステレオ表示** | 左右の目に異なる映像が見える | エンコード時の `--cdist`, `--hfov` を確認 |
| **奥行き感** | 自然な立体感がある | IPD (64mm) がシーンスケールに対して適切か確認 |
| **画質** | シャープで色が正しい | 学習ステップ数を増やす / 入力写真を追加 |
| **フローター** | 空中に浮遊するノイズ | より多くの角度から撮影して再学習 |
| **ぼやけ** | 特定の領域がぼやける | その領域のカメラカバレッジが不足。写真を追加 |

---

## トラブルシューティング

### COLMAP が失敗する

**症状**: `COLMAP mapper did not produce a reconstruction`

**対処法**:
1. 写真のオーバーラップが足りない → 追加撮影（1 歩ごとに 1 枚）
2. テクスチャのない面が多い → テクスチャのある物を配置するか、別の被写体を選ぶ
3. 写真の品質が悪い → ブレていないか確認。再撮影
4. GLOMAP を試す → `--sfm-tool glomap`（一部のケースで COLMAP より堅牢）

**確認コマンド**:
```bash
# COLMAP の中間結果を GUI で確認（GUI 版 COLMAP がある場合）
colmap gui --database_path data/colmap/my_scene/database.db \
           --image_path data/scenes/my_scene/images
```

### 3DGS 学習が遅い / メモリ不足

**症状**: `CUDA out of memory` や極端に遅い

**対処法**:
```bash
# 画像を縮小して学習（data_factor=2 で半分のサイズ）
# → train_gaussians.py の gsplat 呼び出し引数を手動変更
# または training_steps を減らす
python -m pipeline --scene my_scene --training-steps 7000
```

### レンダリング結果が真っ黒 / 真っ白

**原因**: カメラが被写体から極端に離れている、または被写体の内側にある

**対処法**:
```bash
# まず学習カメラの位置を確認して、その近くを指定する
# position と look-at の距離が適切か確認
python -m pipeline --scene my_scene --steps render --position 0,0,2 --look-at 0,0,0
```

### MV-HEVC エンコードが失敗する

**症状**: `MV-HEVC encoding requires macOS with Apple Silicon`

**対処法**: エンコードステップは macOS でのみ実行可能。Linux/Windows で学習・レンダリングまで行い、PNG を Mac に転送して macOS 上でエンコードする:
```bash
# Linux/Windows 側
python -m pipeline --scene my_scene --steps sfm,train,render

# Mac 側（data/output/my_scene/ を転送した後）
cd /path/to/parallaxis
python -m pipeline --scene my_scene --steps encode
```

---

## 出力ファイル一覧

パイプライン実行後、以下のファイルが生成される:

```
data/
├── scenes/my_scene/images/     # 入力写真（自分で配置）
├── colmap/my_scene/
│   ├── database.db             # COLMAP データベース
│   └── sparse/0/
│       ├── cameras.bin         # カメラ内部パラメータ
│       ├── images.bin          # カメラ姿勢（各写真の位置・向き）
│       └── points3D.bin        # スパース 3D 点群
├── models/my_scene/
│   ├── ckpt_29999.pt           # gsplat チェックポイント（レンダリングに使用）
│   └── point_cloud.ply         # エクスポートされた Gaussian Splats
└── output/my_scene/
    ├── left.png                # 左目レンダリング
    ├── right.png               # 右目レンダリング
    ├── left.heic               # HEIC 変換後
    ├── right.heic              # HEIC 変換後
    └── spatial_photo.heic      # 最終成果物 → Vision Pro で閲覧
```

### PLY ファイルの直接閲覧

MV-HEVC エンコードを経由せずに、3DGS シーンを Vision Pro で直接閲覧することも可能:

1. `data/models/my_scene/point_cloud.ply` を Vision Pro に転送
2. **MetalSplatter** アプリ（App Store）で開く
3. 6DoF で自由に視点移動しながら閲覧できる

これはパイプラインの品質確認にも有用。MV-HEVC 変換前に 3DGS シーン自体の品質を確認できる。
