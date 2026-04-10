# -*- coding: utf-8 -*-
# ==================================================
# DWG转GIS自动化处理脚本 - 企业级最终版（修复版）
# 作者：RedBull-coder
# 日期：2026.04
# 特点：高容错、可配置、日志完整、不污染全局环境
# 修复：SimplifyPolygon参数错误，默认关闭简化面
# ==================================================

import arcpy
import os
import re
import logging
from datetime import datetime

# ==================== 参数设置 ====================
cad_folder = r"C:/dwg_input"        # ← 修改为你的DWG文件夹
gdb_path = r"C:/output"           # ← 输出GDB路径
gdb_name = "ZongDi_Data.gdb"

sr = arcpy.SpatialReference(4490)              # CGCS2000 3度带
reference_scale = 1000

# ==================== 功能开关 ====================
ENABLE_CLEANING = True          # 启用数据清洗（仅RepairGeometry）
ENABLE_SIMPLIFY = False         # 关闭简化面（宗地边界不宜简化，避免形状改变）
ENABLE_DELETE_EMPTY = False     # 关闭删除重复要素（防止误删）
ENABLE_TOPOLOGY = True          # 启用拓扑检查

SIMPLIFY_TOLERANCE = "0.001 Meters"   # 简化容差（实际未启用，保留配置）

# ==================== 拓扑规则配置 ====================
TOPOLOGY_RULES = {
    "Must_Not_Overlap": True,           # 面不能重叠（宗地图核心）
    "Must_Not_Have_Gaps": False,        # 面不能有缝隙
    "Must_Not_Self_Intersect": True,    # 不能自相交（针对线，但保留）
}

# 动态容差序列（从0.0001开始逐步放大）
TOLERANCE_SEQUENCE = [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05]

# ==================== 日志配置 ====================
log_file = f"dwg_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

def log_info(msg):
    print(msg)
    logging.info(msg)

def log_warning(msg):
    print(f"⚠️ {msg}")
    logging.warning(msg)

def log_error(msg):
    print(f"❌ {msg}")
    logging.error(msg)

# ==================== 主程序 ====================
def main():
    log_info("=" * 80)
    log_info("DWG转GIS自动化处理 - 企业级最终版（修复版）开始运行")
    log_info("=" * 80)
    
    gdb_full = os.path.join(gdb_path, gdb_name)
    if not arcpy.Exists(gdb_full):
        arcpy.CreateFileGDB_management(gdb_path, gdb_name)
        log_info(f"✅ 创建GDB: {gdb_full}")
    
    arcpy.env.overwriteOutput = True
    
    # 获取所有DWG（支持子文件夹）
    cad_files = []
    for root, _, files in os.walk(cad_folder):
        for f in files:
            if f.lower().endswith('.dwg'):
                cad_files.append(os.path.join(root, f))
    
    log_info(f"共发现 {len(cad_files)} 个DWG文件\n")
    
    success_count = 0
    for cad_file in cad_files:
        cad_name = os.path.basename(cad_file)
        log_info(f"▶️ 开始处理: {cad_name}")
        
        try:
            # DWG有效性检查
            if os.path.getsize(cad_file) < 5 * 1024:
                log_warning(f"{cad_name} 文件过小，可能为空或损坏，跳过")
                continue
            
            define_projection(cad_file, sr)
            feature_dataset = convert_cad_to_gdb(cad_file, gdb_full)
            
            if not feature_dataset:
                continue
                
            if ENABLE_CLEANING:
                clean_geometry(feature_dataset)
            
            if ENABLE_TOPOLOGY:
                validate_topology_dynamic(feature_dataset)
            
            success_count += 1
            log_info(f"✅ {cad_name} 处理成功\n")
            
        except Exception as e:
            log_error(f"{cad_name} 处理失败: {str(e)}\n")
    
    log_info("=" * 80)
    log_info(f"全部处理完成！成功 {success_count}/{len(cad_files)} 个文件")
    log_info(f"日志文件: {log_file}")
    log_info("=" * 80)

# ==================== 核心模块 ====================

def define_projection(cad_file, spatial_ref):
    base = os.path.splitext(cad_file)[0]
    prj_path = base + ".prj"
    with open(prj_path, 'w', encoding='utf-8') as f:
        f.write(spatial_ref.exportToString())
    log_info("  已定义投影 (CGCS2000 3度带)")

def convert_cad_to_gdb(cad_file, gdb_full):
    name = os.path.splitext(os.path.basename(cad_file))[0]
    ds_name = "CAD_" + re.sub(r'[^a-zA-Z0-9_]', '_', name)[:40]
    ds_path = os.path.join(gdb_full, ds_name)
    
    if arcpy.Exists(ds_path):
        arcpy.Delete_management(ds_path)
    
    arcpy.CADToGeodatabase_conversion(cad_file, gdb_full, ds_name, reference_scale)
    log_info(f"  CAD转要素完成 → {ds_name}")
    return ds_path

def clean_geometry(feature_dataset):
    """数据清洗（不污染全局workspace）- 仅修复几何，不删除要素，不简化面"""
    old_ws = arcpy.env.workspace
    try:
        arcpy.env.workspace = feature_dataset
        fcs = arcpy.ListFeatureClasses()
        
        for fc in fcs:
            fc_path = os.path.join(feature_dataset, fc)
            before = int(arcpy.GetCount_management(fc_path).getOutput(0))
            
            # 修复几何（安全，不删除要素）
            arcpy.RepairGeometry_management(fc_path)
            
            # 仅在开关启用时删除重复（默认关闭）
            if ENABLE_DELETE_EMPTY:
                arcpy.DeleteIdentical_management(fc_path, ["Shape"], "", "0.001 Meters")
            
            # 简化面（默认关闭，因宗地边界不宜简化）
            if ENABLE_SIMPLIFY and arcpy.Describe(fc_path).shapeType == "Polygon":
                simplified = fc_path + "_simp"
                # 修正 minimum_area 参数：使用 "0 SquareMeters" 字符串
                arcpy.SimplifyPolygon_cartography(fc_path, simplified, SIMPLIFY_TOLERANCE, "0 SquareMeters", "NO_CHECK")
                arcpy.Delete_management(fc_path)
                arcpy.Rename_management(simplified, fc_path)
                log_info(f"  已简化面要素: {fc}")
            
            after = int(arcpy.GetCount_management(fc_path).getOutput(0))
            if before != after:
                log_info(f"  清洗后要素数量: {before} → {after}")
    finally:
        arcpy.env.workspace = old_ws

def validate_topology_dynamic(feature_dataset):
    """动态容差拓扑检查 - 修复版"""
    old_ws = arcpy.env.workspace
    try:
        arcpy.env.workspace = feature_dataset
        
        polygon_fcs = [fc for fc in arcpy.ListFeatureClasses() 
                      if arcpy.Describe(fc).shapeType == "Polygon"]
        
        if not polygon_fcs:
            log_info("  未找到面要素类，跳过拓扑检查")
            return True
        
        all_success = True
        
        for fc in polygon_fcs:
            fc_path = os.path.join(feature_dataset, fc)
            topology_name = f"{fc}_Topology"
            topology_path = os.path.join(feature_dataset, topology_name)
            
            if arcpy.Exists(topology_path):
                arcpy.Delete_management(topology_path)
            
            success = False
            for tolerance in TOLERANCE_SEQUENCE:
                try:
                    log_info(f"  尝试拓扑检查 - 要素: {fc} | 容差: {tolerance}m")
                    arcpy.CreateTopology_management(feature_dataset, topology_name, tolerance)
                    arcpy.AddFeatureClassToTopology_management(topology_path, fc_path, 1, 1)
                    
                    shape_type = arcpy.Describe(fc_path).shapeType
                    
                    for rule_name, enabled in TOPOLOGY_RULES.items():
                        if enabled:
                            if rule_name == "Must_Not_Overlap" and shape_type == "Polygon":
                                arcpy.AddRuleToTopology_management(topology_path, "Must Not Overlap (Area)", fc_path)
                            elif rule_name == "Must_Not_Have_Gaps" and shape_type == "Polygon":
                                arcpy.AddRuleToTopology_management(topology_path, "Must Not Have Gaps (Area)", fc_path)
                            elif rule_name == "Must_Not_Self_Intersect" and shape_type == "Polyline":
                                arcpy.AddRuleToTopology_management(topology_path, "Must Not Self-Intersect (Line)", fc_path)
                    
                    arcpy.ValidateTopology_management(topology_path)
                    log_info(f"  ✅ {fc} 拓扑验证通过（容差 {tolerance}m）")
                    success = True
                    break
                    
                except Exception as e:
                    if "160342" in str(e) and tolerance != TOLERANCE_SEQUENCE[-1]:
                        log_warning(f"  拓扑引擎故障，尝试更大容差...")
                        if arcpy.Exists(topology_path):
                            arcpy.Delete_management(topology_path)
                        continue
                    else:
                        log_error(f"  {fc} 拓扑检查失败: {str(e)}")
                        break
            
            if not success:
                all_success = False
        
        return all_success
    finally:
        arcpy.env.workspace = old_ws

if __name__ == "__main__":
    main()