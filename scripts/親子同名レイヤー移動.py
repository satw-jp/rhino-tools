# -*- coding: utf-8 -*-
import Rhino
import scriptcontext as sc
import System  # エラー解消のために追加

def move_children_objects_to_same_name_parent():
    # 処理中に画面がチカチカするのを防ぐ
    sc.doc.Views.RedrawEnabled = False
    
    # ドキュメント内のすべてのレイヤーを取得
    layers = sc.doc.Layers
    move_count = 0

    for layer in layers:
        # 削除されたレイヤーはスキップ
        if layer.IsDeleted:
            continue
            
        # 親レイヤーが存在する場合のみ処理（IDが空（Empty）ではない場合）
        if layer.ParentLayerId != System.Guid.Empty:
            parent_layer = layers.FindId(layer.ParentLayerId)
            
            # 親レイヤーが存在し、かつ「親と子が同じ名前」であるかチェック
            if parent_layer and layer.Name == parent_layer.Name:
                
                # この子レイヤーに入っているオブジェクトをすべて取得
                rhino_objects = sc.doc.Objects.FindByLayer(layer)
                
                if rhino_objects:
                    for obj in rhino_objects:
                        # オブジェクトのレイヤーインデックスを親レイヤーに変更
                        obj.Attributes.LayerIndex = parent_layer.Index
                        obj.CommitChanges()
                        move_count += 1

    # 画面を更新して結果を表示
    sc.doc.Views.RedrawEnabled = True
    
    # 結果を表示
    message = u"処理完了: 合計 {} 個のオブジェクトを親レイヤーに移動しました。".format(move_count)
    print(message)

if __name__ == "__main__":
    move_children_objects_to_same_name_parent()
