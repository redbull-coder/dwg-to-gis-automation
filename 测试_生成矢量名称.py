import arcpy
import os

# 测试单个文件
cad_file = r"C:\Users\11.dwg"
gdb_path = r"C:\Users\11.gdb"
output_name = "Test_JB01002"
reference_scale = 1000

try:
    arcpy.CADToGeodatabase_conversion(cad_file, gdb_path, output_name, reference_scale)
    print("转换成功！")

    # 检查结果
    dataset_path = os.path.join(gdb_path, output_name)
    print(f"输出数据集: {dataset_path}")

    # 列出所有要素类
    arcpy.env.workspace = dataset_path
    fcs = arcpy.ListFeatureClasses()
    print(f"包含的要素类: {fcs}")

    for fc in fcs:
        count = int(arcpy.GetCount_management(fc).getOutput(0))
        print(f"  - {fc}: {count}个要素")

except Exception as e:
    print(f"转换失败: {str(e)}")