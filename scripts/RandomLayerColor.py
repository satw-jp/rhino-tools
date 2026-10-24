# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs
import random

def assign_random_colors():
    # ドキュメント内のすべてのレイヤー名を取得
    layer_names = rs.LayerNames()
    
    if not layer_names:
        return

    # 画面の更新を一時停止（処理を高速化するため）
    rs.EnableRedraw(False)
    
    for layer in layer_names:
        # 0〜255の間でRGBの値をランダムに生成
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        
        # レイヤーに色を適用
        rs.LayerColor(layer, [r, g, b])
        
    # 画面の更新を再開
    rs.EnableRedraw(True)

if __name__ == "__main__":
    assign_random_colors()
