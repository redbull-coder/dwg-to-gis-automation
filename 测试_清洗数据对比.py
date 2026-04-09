import arcpy

# 清洗前的要素类路径（需要有备份！！）
before_fc = r"路径\清洗前的要素类"
after_fc = r"路径\清洗后的要素类"

# 比较两个要素类的OBJECTID，找出被删除的
before_ids = set([row[0] for row in arcpy.da.SearchCursor(before_fc, ["OBJECTID"])])
after_ids = set([row[0] for row in arcpy.da.SearchCursor(after_fc, ["OBJECTID"])])
deleted_ids = before_ids - after_ids
print(f"被删除的OBJECTID: {sorted(deleted_ids)}")

# 查看被删除的要素的面积
with arcpy.da.SearchCursor(before_fc, ["OBJECTID", "SHAPE@AREA"]) as cursor:
    for oid, area in cursor:
        if oid in deleted_ids:
            print(f"  要素 {oid}: 面积 {area} 平方米")