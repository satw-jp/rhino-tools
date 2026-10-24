# -*- coding: utf-8 -*-
import Rhino
import scriptcontext as sc
import System.Drawing

def create_sublayers_and_materials_by_color_selected():
    # 1. 選択されたオブジェクトのみを取得する設定
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.NormalObjects = True
    settings.LockedObjects = False   # 選択不可のためFalse
    settings.HiddenObjects = False   # 選択不可のためFalse
    settings.SelectedObjectsFilter = True  # 【修正】選択されているオブジェクトのみをフィルター
    
    # 選択オブジェクトの一覧を取得
    rhino_objects = sc.doc.Objects.GetObjectList(settings)
    
    # パフォーマンス向上のため画面更新を停止
    sc.doc.Views.RedrawEnabled = False
    
    # 処理を実行したかどうかのフラグ
    has_executed = False
    
    try:
        for obj in rhino_objects:
            has_executed = True
            
            # 2. オブジェクト固有の色を持っていない（By Layerなど）場合はスキップ
            if obj.Attributes.ColorSource != Rhino.DocObjects.ObjectColorSource.ColorFromObject:
                continue
                
            # オブジェクトの色を取得
            color = obj.Attributes.ObjectColor
            r, g, b = color.R, color.G, color.B
            
            # 3. 命名規則の定義
            name_suffix = "{}_{}_{}".format(r, g, b)
            mat_name = "Mat_" + name_suffix
            layer_name = "Color_" + name_suffix
            
            # 4. 親レイヤの取得
            parent_layer_index = obj.Attributes.LayerIndex
            parent_layer = sc.doc.Layers[parent_layer_index]
            
            # 5. マテリアルの検索または作成
            mat_index = sc.doc.Materials.Find(mat_name, True)
            
            if mat_index < 0:
                new_mat = Rhino.DocObjects.Material()
                new_mat.Name = mat_name
                new_mat.DiffuseColor = color
                mat_index = sc.doc.Materials.Add(new_mat)
            
            # 6. サブレイヤの検索または作成、マテリアルの割り当て
            sub_layer_index = sc.doc.Layers.Find(layer_name, True)
            
            if sub_layer_index >= 0:
                sub_layer = sc.doc.Layers[sub_layer_index]
                if sub_layer.ParentLayerId != parent_layer.Id:
                    sub_layer_index = -1
                else:
                    # 既存レイヤのマテリアル更新
                    if sub_layer.RenderMaterialIndex != mat_index:
                        sub_layer.RenderMaterialIndex = mat_index
                        sc.doc.Layers.Modify(sub_layer, sub_layer_index, True)
            
            if sub_layer_index < 0:
                new_sub_layer = Rhino.DocObjects.Layer()
                new_sub_layer.Name = layer_name
                new_sub_layer.ParentLayerId = parent_layer.Id
                new_sub_layer.Color = color
                new_sub_layer.RenderMaterialIndex = mat_index
                sub_layer_index = sc.doc.Layers.Add(new_sub_layer)
            
            # 7. オブジェクトをサブレイヤに移動し、マテリアルソースをBY LAYERに変更
            obj.Attributes.LayerIndex = sub_layer_index
            obj.Attributes.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromLayer
            
            obj.CommitChanges()
            
        if has_executed:
            print("選択されたオブジェクトの処理が完了しました。")
        else:
            print("オブジェクトが選択されていません。")
        
    except Exception as e:
        print("エラーが発生しました: {}".format(e))
        
    finally:
        # 画面更新を再開
        sc.doc.Views.RedrawEnabled = True
        sc.doc.Views.Redraw()

# 実行
if __name__ == "__main__":
    create_sublayers_and_materials_by_color_selected()
