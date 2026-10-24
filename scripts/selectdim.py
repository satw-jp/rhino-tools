# -*- coding: utf-8 -*-
import rhinoscriptsyntax as rs

def select_dimensions_only():
    # 512 = Annotation (寸法、テキスト、引き出し線など)
    annotations = rs.ObjectsByType(512, select=False)
    
    if not annotations:
        print("No annotations found.")
        return
    
    dim_ids = []
    for obj_id in annotations:
        if rs.IsDimension(obj_id):
            dim_ids.append(obj_id)
            
    if dim_ids:
        rs.SelectObjects(dim_ids)
        print("Selected {} dimensions.".format(len(dim_ids)))
    else:
        print("No dimension objects found.")

if __name__ == "__main__":
    select_dimensions_only()
