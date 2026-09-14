<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/ekonte-lockup-dark.svg">
    <img src="../assets/ekonte-lockup.svg" alt="Ekonte" width="240">
  </picture>
</p>

# Ekonte API · 絵コンテ

[English](../../README.md) · **日本語** · [简体中文](README.zh-CN.md)

**参考動画の構成を再利用し、同じテンポで新しい制作プランをつくる。**

[![Tests](https://github.com/shiki4709/ekonte-api/actions/workflows/ci.yml/badge.svg)](https://github.com/shiki4709/ekonte-api/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/shiki4709/ekonte-api?include_prereleases)](https://github.com/shiki4709/ekonte-api/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)](../../pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)

Ekonteは短尺動画から時間情報付きのビート（制作上の区切り）を抽出し、発話を割り当て、ショットの分類とナレーションの語数上限を付けます。JSONを一度保存すれば、参考動画を再解析せずに別の制作プランを生成できます。

クリエイティブリサーチ、動画編集、制作支援ツールをつくる開発者向けです。Ekonteの絵コンテアプリから切り出したライブラリで、**v0.1は実験的な開発者向けリリース**です。

[デモ](#デモ) · [クイックスタート](#クイックスタート) · [HTTP API](#http-api) · [関連プロジェクト](#関連プロジェクトとの違い) · [開発への参加](../../CONTRIBUTING.md)

## デモ

[![参考動画を4つのビートと語数上限に変換するデモ](../assets/demo-preview.gif)](https://github.com/shiki4709/ekonte-api/blob/main/docs/assets/ekonte-demo.mp4)

**[36秒の動画を見る](https://github.com/shiki4709/ekonte-api/blob/main/docs/assets/ekonte-demo.mp4)** · [静止画](../assets/demo-poster.png) · [字幕・文字起こし](../demo.md#captions-and-transcript) · [実際の出力](../demo-data)

独自に作成した12秒のモーションサンプルから4つのビートを抽出し、同じ解析結果を2つの制作指示に使います。無言ビートに追加したセリフは検証関数が検出します。実際のAPI出力を編集して可視化したもので、リアルタイムの画面収録ではありません。音声はなく、画面内の説明は英語です。英語・日本語・中国語の字幕ファイルを同梱しています。

## 特徴

- **構成を次の入力にできる。** タイミング、ショット種別、アングル、ビートの役割を明示的なフィールドとして引き継ぎます。
- **無言の区間を制約として扱う。** sensoryやspectacleの分類方針に従い、一部のビートに語数上限0を設定します。生成時もビート単位の書き直し時も、該当する`line`は`null`になります。
- **テンポを検証できる。** 発話データがあれば参考動画の発話速度から語数上限を求めます。モデルを使わない検証関数が、上限超過、構成の変更、ビートの欠落・重複を検出します。最後のビートも対象です。
- **固定カメラの動画にも代替処理がある。** カットが少ない場合は、画面内の変化や文単位の推定境界を使います。
- **不明な情報を不明のまま返す。** 文字起こしの欠落を「無言」とはみなしません。モデルによる分類や推定の単語割り当ては、スキーマで区別します。
- **必要な機能だけ導入できる。** オフライン抽出はコアパッケージとFFmpegで動作します。HTTPサーバー、Gemini、PySceneDetect、SNSダウンローダーは追加機能です。

制作プランをつくるツールです。完成動画のレンダリングや、バズ・視聴維持率の予測は行いません。

## クイックスタート

Python 3.11以上とFFmpeg／ffprobeが必要です。

```bash
# macOS: brew install ffmpeg
# Ubuntu/Debian: sudo apt-get install ffmpeg

git clone https://github.com/shiki4709/ekonte-api.git
cd ekonte-api
python -m venv .venv
source .venv/bin/activate
pip install -e '.[api,gemini]'

python examples/make_demo.py /tmp/ekonte-demo.mp4
ekonte analyze /tmp/ekonte-demo.mp4 --offline -o analysis.json
```

オフラインモードではタイミングと、指定した場合はキーフレームを抽出します。映像の意味分類や文字起こしは行いません。コアのみなら`pip install -e .`で導入できます。このリリースはGitHubからインストールするもので、PyPIには公開していません。

## 一度解析して、複数のプランに使う

```bash
export GOOGLE_API_KEY='your-key'
ekonte analyze reference.mp4 -o analysis.json

ekonte storyboard analysis.json --brief 'Show how our ceramic cup is made.' -o cup.json
ekonte storyboard analysis.json --brief 'Show the texture of our handmade soap.' -o soap.json
```

オンライン解析では抽出した音声とキーフレームをGeminiに送り、生成時には制作指示と解析結果のテキストを送ります。利用料金は自分のプロバイダーアカウントに発生します。オフライン解析とテンポ検証はモデルを呼び出しません。既定モデルは`gemini-2.5-flash`で、`EKONTE_MODEL`で変更できます。変更先はプロバイダー実装のJSON Schemaと設定に対応している必要があります。

```python
from ekonte import analyze, storyboard, StoryboardRequest, validate_pacing
from ekonte.providers import GeminiProvider

provider = GeminiProvider()
analysis = analyze('reference.mp4', provider=provider)
plan = storyboard(
    StoryboardRequest(analysis=analysis, brief='Show how our ceramic cup is made.'),
    provider=provider,
)
print(plan.model_dump_json(indent=2))
print(validate_pacing(analysis, plan.beats))
```

自分の文字起こしを使う場合は、`from ekonte import Segment`を追加し、`transcript=[Segment(start=0, end=2, text='...')]`を渡します。`[]`は「発話がないと分かっている」場合だけ指定してください。`include_keyframes=True`でbase64形式のJPEGを返せます。独自プロバイダーは`complete(prompt, media, schema)`を実装します。同梱プロバイダーはGeminiのみです。

## HTTP API

```bash
export EKONTE_API_KEY='choose-a-long-random-token'
ekonte serve

curl -X POST 'http://127.0.0.1:8421/v1/analyses?offline=true' \
  -H "Authorization: Bearer $EKONTE_API_KEY" \
  -H 'Content-Type: application/octet-stream' \
  --data-binary @/tmp/ekonte-demo.mp4

curl -H "Authorization: Bearer $EKONTE_API_KEY" \
  http://127.0.0.1:8421/v1/jobs/REPLACE_WITH_JOB_ID
```

動画はmultipartではなく、生のバイト列として送信します。ローカルの対話型APIドキュメントは`http://127.0.0.1:8421/docs`、OpenAPIは`/openapi.json`です。`state`が`succeeded`または`failed`になるまでポーリングし、`result`を読みます。結果の保持期間は24時間で、期限切れは404になります。

| エンドポイント | 入力 | 出力 |
|---|---|---|
| `POST /v1/analyses` | 動画バイト列。`offline`、`include_keyframes`を指定可能 | 202とジョブ情報 |
| `GET /v1/jobs/{id}` | ジョブID | 状態、処理段階、結果／エラー |
| `POST /v1/storyboards` | `{analysis, brief, creator_mode}` | 202とジョブ情報 |
| `POST /v1/storyboards/beat/rewrite` | `{analysis, brief, creator_mode, storyboard, beat_id}` | 202とジョブ情報 |
| `POST /v1/pacing/validate` | `{analysis, beats}` | `{valid, violations}`。モデル不要 |

制作プランのリクエストには、ジョブ情報全体ではなく完了済みの`result`を`analysis`として渡します。[実行可能なHTTP例](../../examples/http_workflow.py)と[スキーマの説明（英語）](../schema.md)も参照してください。

## 関連プロジェクトとの違い

2026年9月14日に各プロジェクトの公開READMEを確認した、対象範囲の比較です。品質ベンチマークではありません。

| プロジェクト | 公開ドキュメント上の主な用途 | Ekonteの重点 |
|---|---|---|
| [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | カット・トランジションの検出と分割 | 検出に発話の割り当てと制作上の制約を加える。追加依存として利用可能 |
| [BrightWayAI/video-analyzer](https://github.com/BrightWayAI/video-analyzer) | フレーム解析、文字起こし、スタイル分類、絵コンテ化、MCP | 最も近い用途。Ekonteは新しい制作指示への構成の転用と、ビート単位の語数制約・検証に重点 |
| [VideoDB Director](https://github.com/video-db/Director) | VideoDB上の検索・編集・生成・配信エージェント | ローカルの小さなPythonライブラリと任意のHTTP APIによる制作計画 |
| [AI-storyboard-generator](https://github.com/dseditor/AI-storyboard-generator) | 初期画像とストーリー概要から絵コンテ・動画を生成 | 既存動画から構成を取り出し、新しい文章ベースの制作プランに使う |

[詳細な比較（英語）](../comparison.md)。機能の独占性や出力品質の優位性は主張していません。

## デプロイと制限

```bash
docker build -t ekonte-api .
docker run --rm -p 127.0.0.1:8421:8421 \
  -e GOOGLE_API_KEY -e EKONTE_API_KEY \
  -v ekonte-data:/data ekonte-api
```

- データディレクトリごとにサーバープロセスは1つです。ワーカースレッドは2つ、受け付けるジョブ／アップロードは合計8つまでで、満杯の場合は429を返します。SQLiteの完了結果は再起動後も残ります。中断した処理は失敗扱いになり、自動再実行はしません。
- 入力は180秒、100 MiB、3840×2160まで、出力は60ビートまでです。JSONリクエストは2 MiBまでです。FFmpegの個別実行とプロバイダーリクエストにはタイムアウトがあります。
- アップロードした動画は処理後に削除し、中断で残ったファイルは次回起動時に削除します。結果には発話、画面内テキスト、任意のキーフレームが期限まで残ることがあります。期限切れはDB行の削除であり、安全なディスク消去ではありません。
- 信頼できるユーザー／チーム向けです。1つのBearerトークンで全ジョブにアクセスでき、ユーザー別の分離はありません。外部公開時はHTTPSとアップロード・リクエストのタイムアウトを設定したリバースプロキシを使ってください。CLIはループバック以外へのバインドに`EKONTE_API_KEY`を要求します。FFmpegは敵対的なメディア用の強固なサンドボックスではありません。
- 意味分類、文の境界、発話速度、動画形式の分類は実動画での評価が必要です。語数計算は空白区切りが前提なので、主に英語などに適しています。**この日本語訳は、日本語ナレーションの語数上限が検証済みであることを意味しません。** 強制アラインメントや視聴維持率のベンチマークはありません。
- 生成時は構成と無言の制約を固定し、語数調整を1回試行して、残る違反を報告します。事実性や独創性は保証しません。制作前に内容を確認してください。

`pip install -e '.[scenes]'`でPySceneDetectを追加できます。未導入時はFFmpegを使います。`pip install -e '.[download]'`でTikTok／InstagramのHTTPSリンクをCLIから解析できます。URL取得はCLI／Python向けで、HTTP APIにはありません。処理する権利のある動画を使い、配信元の制約を確認してください。

## 開発・ドキュメント

```bash
pip install -e '.[api,gemini,dev]'
pytest -q
ruff check src tests examples
python -m build
```

テストは合成動画とテスト用プロバイダーを使い、APIキーや有料サービスは不要です。

[参加ガイド](../../CONTRIBUTING.md) · [トラブルシューティング](../troubleshooting.md) · [ロードマップ](../../ROADMAP.md) · [変更履歴](../../CHANGELOG.md) · [セキュリティ](../../SECURITY.md) · [コミュニティ方針](../../CODE_OF_CONDUCT.md)

MITライセンスです。FFmpeg、追加依存、元動画、フォントはそれぞれのライセンスに従います。[アセットの出典](../assets/README.md)。

---

翻訳元：英語README、API v0.1.0、2026年9月14日更新。仕様の基準は[英語版](../../README.md)です。リンク先の技術文書の一部は英語です。翻訳の修正も歓迎します。
