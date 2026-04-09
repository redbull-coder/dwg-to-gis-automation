# -*- coding: utf-8 -*-
# ==================================================
# 批量CAD宗地图数据处理脚本（含数据清洗）
# 功能：1. 定义投影 2. CAD转要素 3. 数据清洗 4. 拓扑检查
# ==================================================

import arcpy
import os
import re

# ==================== 参数设置 ====================

cad_folder = r"C:\Users"   # DWG所在目录
gdb_path = r"C:\Users"   # 矢量存放目录
gdb_name = "宗地数据.gdb" # 数据库名称

# 拓扑检查簇容差（单位：米）
CLUSTER_TOLERANCE = 0.001   # 1毫米，适合宗地数据

# 是否启用数据清洗（强烈建议启用）
ENABLE_CLEANING = True

# 坐标系参数（CGCS2000 3度带，中央经线117°E）
sr_string = (
    "PROJCS['CGCS2000_3_Degree_GK_CM_117E',"
    "GEOGCS['GCS_China_2000',"
    "DATUM['D_China_2000',"
    "SPHEROID['CGCS2000',6378137.0,298.257222101]],"
    "PRIMEM['Greenwich',0.0],"
    "UNIT['Degree',0.0174532925199433]],"
    "PROJECTION['Gauss_Kruger'],"
    "PARAMETER['False_Easting',500000.0],"
    "PARAMETER['False_Northing',0.0],"
    "PARAMETER['Central_Meridian',117.0],"
    "PARAMETER['Scale_Factor',1.0],"
    "PARAMETER['Latitude_Of_Origin',0.0],"
    "UNIT['Meter',1.0]]"
)

sr = arcpy.SpatialReference()
sr.loadFromString(sr_string)
print(sr.name)

reference_scale = 1000

# ==================== 1. 准备工作 ====================
def create_geodatabase(gdb_path, gdb_name):
    full_gdb_path = os.path.join(gdb_path, gdb_name)
    if not arcpy.Exists(full_gdb_path):
        arcpy.CreateFileGDB_management(gdb_path, gdb_name)
        print(f"已创建文件地理数据库: {full_gdb_path}")
    else:
        print(f"文件地理数据库已存在: {full_gdb_path}")
    return full_gdb_path

def define_projection_for_cad(cad_file, sr=None):
    cad_dir = os.path.dirname(cad_file)
    cad_basename = os.path.splitext(os.path.basename(cad_file))[0]
    prj_target = os.path.join(cad_dir, cad_basename + ".prj")
    if sr is not None:
        with open(prj_target, 'w') as f:
            f.write(sr.exportToString())
    print(f"已为 {cad_basename} 定义投影")
    return prj_target

# ==================== 2. 数据清洗 ====================
def clean_geometry(feature_dataset):
    """
    对要素数据集内的所有要素类执行几何修复
    包括：修复几何、移除空几何、简化（可选）
    """
    if not ENABLE_CLEANING:
        print("数据清洗已禁用")
        return True
    
    if not arcpy.Exists(feature_dataset):
        print(f"要素数据集不存在，跳过清洗: {feature_dataset}")
        return False
    
    arcpy.env.workspace = feature_dataset
    all_fcs = arcpy.ListFeatureClasses()
    
    if not all_fcs:
        print("未找到要素类，跳过清洗")
        return False
    
    print("开始数据清洗...")
    for fc in all_fcs:
        fc_path = os.path.join(feature_dataset, fc)
        try:
            # 获取清洗前要素数量
            before_count = int(arcpy.GetCount_management(fc_path).getOutput(0))
            
            # 1. 修复几何（自动处理自相交、空几何、短环等）
            arcpy.RepairGeometry_management(fc_path)
            print(f"  已修复几何: {fc}")
            
            # 2. 删除空几何（如果有）
            arcpy.DeleteIdentical_management(fc_path, ["Shape"], "", "0.001 Meter")
            
            # 3. 可选：简化面（去除冗余顶点，提高拓扑性能）
            # 注意：简化会略微改变边界，对高精度数据慎用
            # 这里暂不启用，如需启用取消下面注释
            # if "polygon" in fc.lower():
            #     simplified = fc_path + "_simplified"
            #     arcpy.SimplifyPolygon_cartography(fc_path, simplified, "0.01 Meters", 0, "NO_CHECK")
            #     arcpy.Delete_management(fc_path)
            #     arcpy.Rename_management(simplified, fc_path)
            
            after_count = int(arcpy.GetCount_management(fc_path).getOutput(0))
            if before_count != after_count:
                print(f"    清洗后要素数量变化: {before_count} -> {after_count}")
                
        except Exception as e:
            print(f"  清洗 {fc} 时出错: {str(e)}")
    
    print("数据清洗完成")
    return True

# ==================== 3. CAD转要素 ====================
def convert_cad_to_geodatabase(cad_file, gdb_path, reference_scale):
    cad_name = os.path.splitext(os.path.basename(cad_file))[0]
    
    # 提取数字ID，使用纯英文输出名称
    match = re.search(r'(\d+[A-Za-z]*\d*)', cad_name)
    if match:
        output_feature_dataset = f"Parcel_{match.group(1)}"
    else:
        output_feature_dataset = re.sub(r'[\u4e00-\u9fff]', '', cad_name)
        output_feature_dataset = re.sub(r'[^a-zA-Z0-9]', '_', output_feature_dataset)
        if not output_feature_dataset:
            output_feature_dataset = f"Parcel_{cad_name[:15]}"
    
    existing_dataset = os.path.join(gdb_path, output_feature_dataset)
    if arcpy.Exists(existing_dataset):
        arcpy.Delete_management(existing_dataset)
        print(f"已删除已存在的数据集: {output_feature_dataset}")
    
    try:
        arcpy.CADToGeodatabase_conversion(
            cad_file, gdb_path, output_feature_dataset, reference_scale
        )
        print(f"CAD转要素完成: {os.path.basename(cad_file)} -> {output_feature_dataset}")
        
        feature_dataset = os.path.join(gdb_path, output_feature_dataset)
        
        # 统计并显示各要素类
        arcpy.env.workspace = feature_dataset
        all_fcs = arcpy.ListFeatureClasses()
        
        polygon_fc = None
        polygon_count = 0
        for fc in all_fcs:
            fc_lower = fc.lower()
            try:
                count = int(arcpy.GetCount_management(fc).getOutput(0))
            except:
                count = 0
            
            if 'polygon' in fc_lower and count > 0:
                polygon_fc = fc
                polygon_count = count
                print(f"  - {fc}: {count}个面要素")
            elif 'polyline' in fc_lower and count > 0:
                print(f"  - {fc}: {count}个线要素")
            elif 'point' in fc_lower and count > 0:
                print(f"  - {fc}: {count}个点要素")
            elif 'annotation' in fc_lower and count > 0:
                print(f"  - {fc}: {count}个注记")
        
        return feature_dataset, polygon_fc, polygon_count
        
    except Exception as e:
        print(f"CAD转要素失败: {os.path.basename(cad_file)}, 错误: {str(e)}")
        return None, None, 0

# ==================== 4. 拓扑检查 ====================
def create_and_validate_topology(feature_dataset, polygon_fc_name, polygon_count, cluster_tolerance=0.01):
    if not arcpy.Exists(feature_dataset):
        print(f"要素数据集不存在: {feature_dataset}")
        return False
    
    if polygon_fc_name is None:
        print("没有找到面要素类，跳过拓扑检查")
        return False
    
    arcpy.env.workspace = feature_dataset
    fc_path = os.path.join(feature_dataset, polygon_fc_name)
    
    if not arcpy.Exists(fc_path):
        print(f"要素类不存在: {fc_path}，跳过拓扑检查")
        return False
    
    topology_name = f"{polygon_fc_name}_Topology"
    topology_path = os.path.join(feature_dataset, topology_name)
    
    if arcpy.Exists(topology_path):
        arcpy.Delete_management(topology_path)
    
    try:
        arcpy.CreateTopology_management(feature_dataset, topology_name, cluster_tolerance)
        print(f"已创建拓扑: {topology_name} (簇容差: {cluster_tolerance}米)")
        
        arcpy.AddFeatureClassToTopology_management(topology_path, fc_path, 1, 1)
        print(f"已将要素类添加到拓扑: {polygon_fc_name}")
        
        rule = "Must Not Overlap (Area)"
        arcpy.AddRuleToTopology_management(topology_path, rule, fc_path, "", "", "")
        print(f"已添加拓扑规则: {rule}")
        
        arcpy.ValidateTopology_management(topology_path)
        print("拓扑验证完成")
        
        # 统计错误
        error_count = 0
        for error_type in ["PointErrors", "LineErrors", "PolygonErrors"]:
            error_path = f"{topology_path}/{error_type}"
            if arcpy.Exists(error_path):
                try:
                    cnt = int(arcpy.GetCount_management(error_path).getOutput(0))
                    error_count += cnt
                except:
                    pass
        
        if error_count > 0:
            print(f"⚠️ 发现 {error_count} 个拓扑重叠错误")
        else:
            print("✅ 拓扑检查通过，未发现重叠错误")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "160342" in error_msg and cluster_tolerance < 0.1:
            print(f"⚠️ 拓扑引擎故障，自动放大簇容差重试...")
            new_tolerance = cluster_tolerance * 10
            return create_and_validate_topology(feature_dataset, polygon_fc_name, polygon_count, new_tolerance)
        print(f"拓扑检查失败: {error_msg}")
        return False

# ==================== 主程序 ====================
def main():
    print("=" * 50)
    print("批量CAD宗地图数据处理开始（含数据清洗）")
    print("=" * 50)
    print(f"拓扑检查簇容差: {CLUSTER_TOLERANCE}米")
    print(f"数据清洗: {'启用' if ENABLE_CLEANING else '禁用'}")
    
    gdb_full_path = create_geodatabase(gdb_path, gdb_name)
    arcpy.env.workspace = gdb_full_path
    
    cad_files = []
    for file in os.listdir(cad_folder):
        if file.lower().endswith(".dwg"):
            cad_files.append(os.path.join(cad_folder, file))
    
    cad_files.sort()
    print(f"共发现 {len(cad_files)} 个DWG文件")
    
    success_count = 0
    topology_checked = 0
    
    for cad_file in cad_files:
        print(f"\n--- 正在处理: {os.path.basename(cad_file)} ---")
        
        define_projection_for_cad(cad_file, sr=sr)
        feature_dataset, polygon_fc, polygon_count = convert_cad_to_geodatabase(cad_file, gdb_full_path, reference_scale)
        
        if feature_dataset and polygon_fc:
            # 数据清洗（关键步骤）
            clean_geometry(feature_dataset)
            
            # 拓扑检查
            result = create_and_validate_topology(feature_dataset, polygon_fc, polygon_count, CLUSTER_TOLERANCE)
            if result:
                topology_checked += 1
            success_count += 1
    
    print(f"\n" + "=" * 50)
    print(f"处理完成！")
    print(f"  - 成功转换: {success_count}/{len(cad_files)} 个CAD文件")
    print(f"  - 拓扑检查完成: {topology_checked} 个")
    print(f"  - 数据保存位置: {gdb_full_path}")
    print("=" * 50)

if __name__ == "__main__":
    main()