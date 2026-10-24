import Rhino
import System.Drawing
import scriptcontext as sc

# アクティブなドキュメントを取得
doc = Rhino.RhinoDoc.ActiveDoc

# すべてのレイヤーを取得
layers = doc.Layers

for layer in layers:
    # レイヤーの表示色（カスタムカラー）を取得
    layer_color = layer.Color
    
    # マテリアル名を作成（例: "Material_R255_G255_B255"）
    mat_name = "Mat_{}_{}_{}".format(layer_color.R, layer_color.G, layer_color.B)
    
    # 同名のマテリアルが既に存在するか確認
    existing_mat_index = -1
    for i, rm in enumerate(doc.RenderMaterials):
        if rm.Name == mat_name:
            existing_mat_index = i
            break
            
    if existing_mat_index != -1:
        # 既存のマテリアルを使用
        new_render_mat = doc.RenderMaterials[existing_mat_index]
    else:
        # 新しい基本マテリアルを作成
        new_render_mat = Rhino.Render.RenderMaterial.CreateBasicMaterial(Rhino.DocObjects.Material())
        new_render_mat.Name = mat_name
        
        # 基本設定の拡散色（Diffuse Color）をレイヤー色に設定
        # (RenderMaterialは直接色を直接代入できないため、XmlParametersを使用)
        xml = "<xml><material><diffuse>{}</diffuse></material></xml>".format(
            System.Drawing.ColorTranslator.ToHtml(layer_color)
        )
        new_render_mat.SetXmlParameters(xml)
        
        # ドキュメントにマテリアルを登録
        doc.RenderMaterials.Add(new_render_mat)
        
    # レイヤーにマテリアルを割り当てる
    layer.RenderMaterial = new_render_mat
    layer.CommitChanges()

print("レイヤーごとのマテリアル割り当てが完了しました。")
