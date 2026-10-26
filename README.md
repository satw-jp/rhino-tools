# Rhino Tools — SATW

Rhinoで日々繰り返す作図・レイヤー整理・色調整・印刷のための、小さなPythonツール集です。**10ツールをこの1ページから探して使えます。**

[選択](#1-選択) ｜ [レイヤー整理](#2-レイヤー整理) ｜ [色・マテリアル](#3-色マテリアル) ｜ [シート・印刷](#4-シート印刷) ｜ [使い方](#使い方) ｜ [注意事項](#注意事項)

> **実機検証について**：既存のシート系3ツールは **Rhino 8 / Windows / ScriptEditor Python 3** を想定しています。追加した7ツールは既存のRhino Pythonコードをそのまま収録したもので、Rhino 8での動作確認・対応版の確定はまだです。このリポジトリでの公開に先立つ実機での回帰テストは完了していません。**必ずモデルを複製して試してください。**

## ツール一覧

### 1. 選択

| ツール | 概要 | 対象・作用 | ファイル |
| --- | --- | --- | --- |
| **寸法をまとめて選択** | 図面内の寸法オブジェクトを追加選択 | 図面全体を検索／選択のみ | [コード](scripts/selectdim.py) · [↓ .py](https://raw.githubusercontent.com/satw-jp/rhino-tools/main/scripts/selectdim.py) |
| **文字・注釈をまとめて選択** | テキスト、引出線、寸法のうち文字を持つ注釈を追加選択 | 図面全体を検索／選択のみ | [コード](scripts/SelectTXT.py) · [↓ .py](https://raw.githubusercontent.com/satw-jp/rhino-tools/main/scripts/SelectTXT.py) |

### 2. レイヤー整理

| ツール | 概要 | 対象・作用 | ファイル |
| --- | --- | --- | --- |
| **親子同名レイヤーのオブジェクト移動** | 親と子の名前が同じとき、子の中のオブジェクトを親へ移す | 図面全体／レイヤー変更 | [コード](scripts/MoveSameNameChildLayerObjects.py) · [↓ .py](https://raw.githubusercontent.com/satw-jp/rhino-tools/main/scripts/MoveSameNameChildLayerObjects.py) |

### 3. 色・マテリアル

**Picture / V-Ray PNGアルファ（診断版・適用未実装）**：
[説明・未検証事項](docs/vray-picture-alpha.md) ·
[診断コード](scripts/rhino8_vray_picture_alpha_probe.py) ·
[テスト](tests/test_vray_picture_alpha_probe.py)。
Rhino 8 Windows / V-Ray 7.40.02を対象に調査中です。
選択物ごとの画像パス候補と連携情報を読み取るdry-runのみで、透明度を修正する最終版ではありません。
適用は安全のため無効です。既存の10ツールの数には含めません。

| ツール | 概要 | 対象・作用 | ファイル |
| --- | --- | --- | --- |
| **レイヤー色をランダム化** | すべてのレイヤーにランダムな表示色を設定 | 図面全体／色変更 | [コード](scripts/RandomLayerColor.py) · [↓ .py](https://raw.githubusercontent.com/satw-jp/rhino-tools/main/scripts/RandomLayerColor.py) |
| **オブジェクト固有色で分類** | 選択オブジェクトをRGB別の子レイヤーに分け、同色材質を設定 | 選択物／レイヤー・材質変更 | [コード](scripts/CustomColor2Layer.py) · [↓ .py](https://raw.githubusercontent.com/satw-jp/rhino-tools/main/scripts/CustomColor2Layer.py) |
| **ハッチを色別レイヤーに分類** | 選択ハッチをRGB別レイヤーに分け、レイヤーに材質を割り当てる | 選択ハッチ／レイヤー・材質変更 | [コード](scripts/Hatch2LayerWithMaterial.py) · [↓ .py](https://raw.githubusercontent.com/satw-jp/rhino-tools/main/scripts/Hatch2LayerWithMaterial.py) |
| **レイヤー色から材質を生成** | 全レイヤーの色を基に材質を作成・再利用して割り当てる | 図面全体／材質変更・要改修 | [コード](scripts/RANDOM3.py) · [↓ .py](https://raw.githubusercontent.com/satw-jp/rhino-tools/main/scripts/RANDOM3.py) |

### 4. シート・印刷

| ツール | 概要 | 対象・作用 | ファイル |
| --- | --- | --- | --- |
| **A3/A4用紙枠を一括配置** | サイズ、縦横、行列数、縮尺を指定し、マウスプレビューで配置 | モデル空間／枠作成 | [コード](scripts/rhino8_sheet_create.py) · [↓ .py](https://raw.githubusercontent.com/satw-jp/rhino-tools/main/scripts/rhino8_sheet_create.py) |
| **連続PDF出力** | 用紙枠を認識して複数ページPDFに出力 | モデル空間／PDF作成 | [コード](scripts/rhino8_sheet_batch_pdf_v03.py) · [↓ .py](https://raw.githubusercontent.com/satw-jp/rhino-tools/main/scripts/rhino8_sheet_batch_pdf_v03.py) |
| **ネイティブレイアウト変換** | 用紙枠をRhinoのレイアウトページ＋詳細ビューに変換 | レイアウトページ作成 | [コード](scripts/rhino8_sheet_to_layout_v04.py) · [↓ .py](https://raw.githubusercontent.com/satw-jp/rhino-tools/main/scripts/rhino8_sheet_to_layout_v04.py) |

## 使い方

1. 上表の **「コード」** を開いて内容を確認し、**「↓ .py」** からスクリプトを保存する（またはリポジトリをZIPで取得）。
2. Rhino 8 の **ScriptEditor** で `.py` を開き、Python環境を選んで実行する。新規追加の7ツールはPython環境との互換性も含めて事前検証する。
3. 対話入力があるツールはRhinoのコマンドラインで指示に従う。実行後、結果を確認してから元ファイルに反映する。

Pythonの追加パッケージはコード上では要求しておらず、主にRhinoCommon／`rhinoscriptsyntax`／`scriptcontext`を使います。ただし**動作保証ではありません**。

### シート・印刷の順番

**① [用紙枠を配置](scripts/rhino8_sheet_create.py) → ② [連続PDF](scripts/rhino8_sheet_batch_pdf_v03.py)**、または **① → ③ [ネイティブレイアウトに変換](scripts/rhino8_sheet_to_layout_v04.py)**。

- 用紙枠の配置は **A3/A4・縦横・1〜30列×1〜30行・縮尺**などを指定し、配置前にプレビューできます。
- `SHEET_FRAME` レイヤーの認識可能な枠からPDFを生成します。PDF出力スクリプトでは300 DPIを設定しています。
- レイアウト変換は詳細ビューポートを作成・ロックします。**変換後のページはモデル変更に追従**します。
- これらのツールは**モデル単位mm・標準Top平行投影**を前提とします。XY平面に軸平行の長方形枠のみ対象です。

<details>
<summary>シート・印刷の詳しい制約と確認事項を開く</summary>

- 用紙サイズはA3（420×297 mm）とA4（297×210 mm）、横向き・縦向きに対応します。
- 配置時の縮尺分母は0.001〜10000、紙上の枠間隔は0〜1000 mmを指定できます。配置プレビューの基準はグリッド左上です。
- PDFはアクティブなTopビューから枠を切り出します。補助線、注釈、枠そのものが含まれることがあります。印刷線幅・色・表示モードは別途確認してください。
- PDFのページ順は、枠のY位置をおよそ10モデル単位で段にまとめてから、上段優先・左から右へ並べます。不規則な配置では意図と異なる場合があります。
- レイアウト変換でページが既にあると通常はスキップします。置き換えを指定したときはツールが識別した生成ページのみ削除対象になり、ユーザー作成の同名ページがあれば停止する設計です。操作の前にバックアップしてください。
- Rhino 8実機でPDF用紙サイズ、縮尺、向き、ページ順、レイアウトの詳細ビュー、印刷表現などをまだ再検証していません。

</details>

## 注意事項

| ツール | 実行前に知っておくこと |
| --- | --- |
| `RandomLayerColor.py` | **選択物に限らずすべてのレイヤー色を変更**します。元の配色を保持したい場合はコピーを作成してください。 |
| `RANDOM3.py` | **要改修・要実機検証**。マテリアル生成APIの互換性に疑義があり、現在のRhino 8での成功を保証できません。 |
| `CustomColor2Layer.py` | 同じオブジェクトへの繰り返し実行で子レイヤーが多重に作られる可能性があります。実行前後に構造を確認してください。 |
| `MoveSameNameChildLayerObjects.py` | 子レイヤーの**オブジェクトのみ**親へ移動します。空になった子レイヤーは削除しません。 |
| `Hatch2LayerWithMaterial.py` | 選択ハッチのRGBに従ってレイヤー・材質が変更されます。元のレイヤー構成を残す場合はコピーで試してください。 |
| `RandomLayerColor.py`・`MoveSameNameChildLayerObjects.py` | エラー時に画面の再描画状態が復帰しない可能性がある旧コードです。公開中ですが改修候補です。 |

**状態**：コードを収録・整理した段階です。個別ツールの互換性・バグ修正・実機検証は順次進めます。質問、不具合、改善案は [GitHub Issues](https://github.com/satw-jp/rhino-tools/issues) へ。

## 開発・管理

- **GitHubを正本**として各ツールを独立した`.py`で管理し、変更履歴はGitで残します。
- PDF出力の `v02` は旧版のため、この一覧では `v03` のみ掲載しています。
- Grasshopperの`.gh`やRhinoプラグインの`.rhp`はこのPythonツール一覧には含めていません。
- ライセンス： [MIT](LICENSE)。

