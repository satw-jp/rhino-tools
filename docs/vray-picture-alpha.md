# Picture / V-Ray PNGアルファ：診断版（適用未実装）

**最終変換ツールではありません。** Rhino 8 Windows / V-Ray 7.40.02での
アルファ修正・レンダリング・保存再読込は未検証です。`dry_run=False` は
ホストへのアクセス前に例外で停止します。材質の作成・割当や透明度変更は行いません。

## 使い方

1. V-RayをロードしたRhino 8で、調べたい既存Pictureを事前選択します。
2. ScriptEditorのPython 3で `scripts/rhino8_vray_picture_alpha_probe.py` を実行します。
3. `rh8VRay` が見つからない場合、V-Rayのインストール先
   `C:\Program Files\Chaos\V-Ray\V-Ray for Rhinoceros` をPythonの検索パスに追加します。
4. 出力のJSONを確認します。ファイルやモデルへの自動保存は行いません。

選択を変更せず、直接割り当てられた従来材質のBitmapスロットから各パスを個別に読みます。
画像パスは推測・置換・共通化しません。このパスがV-Rayの実際の入力であるとは断定しません。
Pictureの自動識別は未実装で、選択物は候補として報告します。
レイヤー／親からの継承、埋込画像、相対パス、RDKのみの材質は対応を推測せず報告します。
PNGは先頭33バイトのヘッダー検査だけです。画素、CRC、tRNS、破損、実際の透明領域は検証しません。

コードは位置・サイズ・形状・UV・材質・選択を変更するAPIを呼びません。
これは**変換後のUV維持を実証したものではありません**。
読取API自体のホスト内の副作用も実機では未検証です。
診断APIの取得に失敗すれば停止またはオブジェクト単位のエラーを報告し、変更処理へ移行しません。

## 確認できたAPIと不足する証拠

調査日：2026-10-26。公開資料は7.40.02固定の仕様書ではありません。

- [Chaos Script Access](https://docs-chaos.atlassian.net/wiki/spaces/VRHINO/pages/116130923/V-Ray%2BScript%2BAccess)：
  CPythonは `import rh8VRay as vray`。
  使用する読取APIは `vray.Version`、`vray.VRayVersion`、
  `vray.Scene.PluginFromObject(str_id)`、プラグインの `Name`、`Type`、`ParamNames`。
  `PluginFromObject` の結果を材質と仮定していません。
  資料には `Param(name).Value`、`Scene.Transaction()` もありますが、本コードでは書込みません。
  例外時のロールバック仕様は確認できず、Transactionを原子性の根拠にできません。
- UI設定に必要なuser-data名は、対象バージョンから出力した `.vrmat` の
  `isUserData="1"` を確認する方式が公式に案内されています。
  7.40.02の書出しデータがないため、opacity設定名・値・接続方式を確定していません。
- [Generic Opacity](https://docs-chaos.atlassian.net/wiki/spaces/VRHINO/pages/116131521)：
  UIにはDiffuse Texture Alphaを透明度に使う設定があります。
  UI名から内部パラメータ名や数値を推測していません。
- [McNeel GetBitmapTexture](https://developer.rhino3d.com/api/rhinocommon/rhino.docobjects.material/getbitmaptexture)：
  従来材質の画像スロット取得に使用。
  [Material.RenderMaterial](https://developer.rhino3d.com/api/rhinocommon/rhino.docobjects.material/rendermaterial)
  はgetterでも新規データを作る場合があるため使用しません。

## テストと限界

リポジトリ直下で `python3 -m unittest discover -s tests -v`。
標準ライブラリとモックによるテストで、適用拒否、個別パスの保持、継承材質の拒否、
読取エラー、PNGヘッダーの判定範囲を確認します。RhinoCommon、COM、V-Ray、実レンダリングの
動作確認ではありません。Windows実機はこの開発環境にありません。

## FOLLOW-UP：最終版に必要な実機作業

1. 7.40.02の `rh8VRay.py` と同梱 `VRayForRhinoObjectModel.html` を照合する。
2. 同一Generic材質をDiffuse Texture Alpha設定の変更前後で `.vrmat` に書き出し、
   user-dataの名前・型・値とBitmap／UV接続を確定する。
3. Pictureの識別、オブジェクト→材質→Bitmapの対応、共有材質の分離方法を確認する。
   画像ごとのパスと既存UV変換を引き継ぐ新規材質をステージングできることを確認する。
4. RhinoとV-Ray双方の変更を復元できることを、途中の例外・割当失敗も含め実証する。
   確認前に適用ガードを解除しない。
5. 異なるPNGのPicture2枚、同じ材質を使う非選択物、回転・拡縮・変更済みUV、
   埋込／欠損画像、途中失敗で検証する。成功時の位置・サイズ・UV・個別パス、
   失敗時の全状態、保存再読込と白／黒背景レンダリングのアルファを比較する。

技術調査の公開であり、production採用や最終版の完成を意味しません。
