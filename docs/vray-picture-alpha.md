# Picture / V-Ray：透明PNGアルファ適用ツール

[コード](../scripts/rhino8_vray_picture_alpha.py) · [ダウンロード](https://raw.githubusercontent.com/satw-jp/rhino-tools/main/scripts/rhino8_vray_picture_alpha.py) · [テスト](../tests/test_vray_picture_alpha.py)

**状態：Apply処理を実装済み。Rhino 8 Windows / V-Ray 7.40.02の実機・実レンダリングは未検証。**
診断専用の旧版と異なり、Applyを選ぶと材質を変更します。実機確認済みの安定版という意味ではありません。

## 何を変更するか

PNGのアルファを同じ画素数の白黒PNGとして抽出し、対象ごとに新規作成したRhino PBR材質の
**Base Colorに各対象の元画像、Alphaにその画像のマスク**を接続して割り当てます。
黒=透明、白=不透明で、反転・二値化・上下反転・リサイズはしません。8bitの中間アルファも保持します。

V-Rayが公式にサポートするRhino PBRの直接レンダリング経路を使用します。
V-Ray Generic材質の「Diffuse Texture Alpha」スイッチを書き換える方式ではありません。
V-Ray内部の設定名・数値を推測した書込み、vrayMtlFromRhinoの自動実行は行いません。

- オブジェクトID、位置、サイズ、形状、既存のオブジェクトUVマッピングを維持します。
  作り直し、Replace、Transform、SetTextureMappingは呼びません。
- BitmapのローカルUV行列・チャンネル・投影方式・繰返しを新規テクスチャへ渡し、変換前後で照合します。
  全オブジェクトマッピングチャンネルの定義と変換も割当前後に照合します。
- 個別パスを読み取り、相対パスだけを3dmの保存先基準で解決します。別画像の同名ファイルを探索して代用しません。
- 元PNGと既存材質は編集しません。共有材質を使う非選択物に新材質を割り当てません。
- **材質の見た目はマットなPBRへ変更されます。Pictureの無照明表示、色補正、自己発光などの完全再現は対象外です。**

## Rhinoでの使い方

1. 元モデルを別名保存して開き、V-Rayのインタラクティブレンダリングを停止します。
2. 既存Pictureをオブジェクト単位で選択します。
3. 上記のPythonファイルを保存し、Rhino 8の **ScriptEditor / Python 3** で実行します。
   先頭の `# r: pillow` はRhinoのパッケージ依存宣言です。初回はPillowの取得が必要です。
4. コマンド出力の対象ID、元画像パス、UV、画像サイズ、アルファ範囲を確認します。
5. **DryRun（既定）** またはキャンセルなら、モデル変更とマスク書出しをしません。
6. **Apply** を選び、マスクを保存しておくフォルダを指定します。
   その配下に `rhino-picture-alpha-...` が作られます。成功後のマスクは外部テクスチャなので削除しないでください。
7. V-Rayでテストレンダリングしてから別名保存します。モデルを移動する場合は元画像とマスクも移動・再設定してください。
   成功した適用はRhinoのUndo記録にまとめます。UndoしてもマスクはRedoの参照先として残します。

選択が空、PNGが欠損、対象が非対応などの場合は、全体を事前検査して適用を中止します。
途中のエラーではスナップショットの属性へ戻し、新規材質・自動生成された従来材質・マスクを削除します。
復元や削除がホスト側でも失敗した場合は **restoration incomplete** と詳細を出し、参照切れを避けるため
残存資材を保持します。その場合は元モデルに上書き保存しないでください。
プロセス強制終了、OS障害、同時実行のスクリプト／レンダリングまで原子性を保証するものではありません。
失敗時のモデル内容を復元する設計で、Undo履歴・dirtyフラグまで完全に巻き戻す設計ではありません。

## 対応範囲

ネイティブのPicture材質と通常のBitmapを持ち、外部PNGを読み取れるPictureが対象です。
RGBA、LA、パレットPNGのtRNSをデコードします。8bit未満のPNGもPillowで8bitマスクに展開します。
16bit PNG、アニメーションPNG、アルファなし／完全不透明PNG、埋込のみで外部ファイルがない画像は拒否します。
ロック／参照／ブロック定義内／面別材質／動的変換中の対象、既にV-Ray材質やPBRへ変換された対象も拒否します。
一度適用した材質を再び変換するツールではありません。やり直しはUndo後に実行してください。
未保存3dmの相対画像パスは解決しません。

## APIの根拠とV-Ray Script Accessの調査結果

調査日：2026-10-26。公開資料は7.40.02専用の仕様書ではありません。

- [Chaos：材質の扱い](https://docs.chaos.com/display/VRHINO/How%2Bto%2BWork%2Bwith%2BMaterials)
  はRhino PBR材質の直接レンダリングを案内しています。この対応を利用する実装です。
- [McNeel：PBRのAlpha](https://docs.mcneel.com/rhino/8/help/en-us/commands/materials.htm)
  は切り抜き用途にAlphaを使うことを説明しています。屈折を起こすOpacity Amountへマスクを入れません。
- [NewContentFromTypeId](https://mcneel.github.io/rhinocommon-api-docs/api/RhinoCommon/html/M_Rhino_Render_RenderContentType_NewContentFromTypeId.htm)
  で一時的なPBR材質を作成し、公開された `ParameterNames.PhysicallyBased` と
  `ChildSlotNames.PhysicallyBased` 定数を使います。
- [RenderTexture.NewBitmapTexture](https://developer.rhino3d.com/api/rhinocommon/rhino.render.rendertexture/newbitmaptexture)
  は既存BitmapのSimulatedTextureからテクスチャを構成します。`TextureGeneration.Disallow` を使い、
  事前検査でテクスチャをベイクしません。UV照合が不一致なら適用を拒否します。
- [RenderMaterialTable](https://mcneel.github.io/rhinocommon-api-docs/api/RhinoCommon/html/T_Rhino_Render_RenderMaterialTable.htm)
  のAdd/Removeと、複製したObjectAttributesのRenderMaterial設定・ModifyAttributesを使用します。
- [Chaos：Script Access](https://docs-chaos.atlassian.net/wiki/spaces/VRHINO/pages/116130923/V-Ray%2BScript%2BAccess)
  で確認できるのはRhino 8 CPythonの `rh8VRay`、`Param(name).Value`、`Scene.Transaction()` などです。
  UI用user-dataは対象版から書き出した `.vrmat` で名前を確認する必要があります。
  7.40.02のGeneric opacityの内部名・値とTransactionの失敗時ロールバックは確認できていません。
  **この適用版はそれらに依存せず、rh8VRayのインポートも要求しません。**

## 実施した検証

`python3 -m pip install pillow` のある環境で、リポジトリ直下から
`python3 -m unittest discover -s tests -v` を実行します。

- 実画像：アルファ値0/64/128/255を画素単位で比較、向き・サイズ維持、パレットtRNS。
- 不正入力：アルファなし、完全不透明、16bit、壊れた画像、欠損・未解決パス。
- 制御：既定dry-runが書込みを呼ばないこと、対象全体の事前検査、個別パスの引継ぎ、画像変更の検知。
- 障害注入：材質生成、Undo開始、材質追加、割当、検証の各失敗後の復元と資材削除。
  変更してから失敗を返すホスト、復元失敗、削除失敗も含みます。
- UV比較：行列・マッピングチャンネル変更を検出すること。

**上記はPNG処理とモックホストによるテストです。RhinoCommonの実動作やV-Rayレンダリングを代替しません。**
2026-10-26のローカル実行結果：適用版14件＋旧診断版8件、計22件成功。
Windows/Rhino/V-Rayはこの開発環境にないため、以下は未検証です。

## FOLLOW-UP：実機受入確認

1. 7.40.02 CPU/GPUそれぞれで、異なる画像を持つPicture2枚を白／黒背景上でレンダリングする。
2. 透明・不透明・半透明の領域、輪郭の色、Alphaスロットの色空間／ガンマを確認する。
   マスクの画素値は保持していますが、レンダラーが中間アルファをどう評価するかは未検証です。
   Base Color側の自動アルファ利用との二重適用の有無も確認が必要です。
3. 回転・拡縮、変更済みのローカルUVと複数マッピングチャンネルで外観を比較する。
   Python.NETのout引数、PictureのDiffuseスロット取得、PBR工場、属性割当・復元を実機確認する。
4. 共有材質を持つ非選択物への影響、保存再読込、Undo/Redo、途中失敗時の材質テーブル削除を確認する。

旧診断版は [rhino8_vray_picture_alpha_probe.py](../scripts/rhino8_vray_picture_alpha_probe.py) に残しています。
