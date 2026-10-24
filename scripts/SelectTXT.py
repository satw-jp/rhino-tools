# -*- coding: utf-8 -*-
import Rhino
import scriptcontext as sc

# 注釈オブジェクト（テキスト、引出線、寸法線すべて）を検索対象にする設定
settings = Rhino.DocObjects.ObjectEnumeratorSettings()
settings.ObjectTypeFilter = Rhino.DocObjects.ObjectType.Annotation
all_annotations = sc.doc.Objects.GetObjectList(settings)

selected_count = 0
for obj in all_annotations:
    if hasattr(obj, "Geometry") and obj.Geometry is not None:
        geom = obj.Geometry
        
        # オブジェクトから文字列を取得
        text_string = ""
        if isinstance(geom, Rhino.Geometry.TextEntity):
            text_string = geom.PlainText
        elif isinstance(geom, Rhino.Geometry.Leader):
            text_string = geom.PlainText
        elif isinstance(geom, Rhino.Geometry.Dimension):
            text_string = geom.PlainText
            
        # 空文字やスペースだけでない「中身のあるテキスト」ならすべて選択
        if text_string and text_string.strip():
            obj.Select(True)
            selected_count += 1

# 画面の描画を更新して選択状態を反映
if selected_count > 0:
    sc.doc.Views.Redraw()
    print("Selected all text objects.")
else:
    print("No text found.")
