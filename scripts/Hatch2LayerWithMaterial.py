# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino

def create_layer_material(layer_name, color):
    """指定した色でレイヤーマテリアルを作成し、レイヤーに割り当てます"""
    # 1. 指定した名前のレイヤーオブジェクトを取得
    layer_index = sc.doc.Layers.FindName(layer_name).Index
    layer = sc.doc.Layers[layer_index]
    
    # 2. すでにマテリアルが設定されている場合はスキップ
    if layer.RenderMaterialIndex >= 0:
        return
        
    # 3. 新しいマテリアルを作成
    material = Rhino.DocObjects.Material()
    material.Name = "Mat_" + layer_name
    material.DiffuseColor = color  # 拡散反射色（基本の色）を設定
    
    # 4. ドキュメントのマテリアルテーブルに追加し、レイヤーにリンク
    mat_index = sc.doc.Materials.Add(material)
    if mat_index >= 0:
        layer.RenderMaterialIndex = mat_index
        layer.CommitChanges()

def sort_hatches_with_materials():
    # ハッチングオブジェクトを選択
    hatch_ids = rs.GetObjects("色ごとにレイヤー分け（マテリアル適用）するハッチングを選択してください", filter=65536, preselect=True)
    if not hatch_ids:
        print("ハッチングが選択されませんでした。")
        return

    # 描画停止（高速化）
    rs.EnableRedraw(False)

    try:
        for h_id in hatch_ids:
            # ハッチングの色（RGB）を取得
            color = rs.ObjectColor(h_id)
            if not color:
                continue
            
            # RGB値からユニークなレイヤー名を作成
            layer_name = "Hatch_{}_{}_{}".format(color.R, color.G, color.B)

            # レイヤーが存在しない場合は新規作成し、色を設定
            if not rs.IsLayer(layer_name):
                rs.AddLayer(layer_name, color)
            
            # 【追加】レイヤーマテリアルを作成して適用
            create_layer_material(layer_name, color)
            
            # ハッチングを新しいレイヤーに移動
            rs.ObjectLayer(h_id, layer_name)
            
            # ハッチングの色とマテリアルを「レイヤー別 (By Layer)」に変更して同期
            rs.ObjectColorSource(h_id, 0)     # 0 = Color By Layer
            rs.ObjectMaterialSource(h_id, 0)  # 0 = Material By Layer

        print("{} 件のハッチングを色別にレイヤー分けし、マテリアルを適用しました。".format(len(hatch_ids)))

    finally:
        # 描画再開
        rs.EnableRedraw(True)

if __name__ == "__main__":
    sort_hatches_with_materials()
