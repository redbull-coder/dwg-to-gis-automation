# 🚀 DWG to GIS Automation (ArcPy) 

> 高容错 | 可配置 | 日志完整 | 宗地数据专用  
> *Batch DWG to Geodatabase conversion with dynamic topology validation.*

[![ArcGIS](https://img.shields.io/badge/ArcGIS-Desktop%20%7C%20Pro-blue)](https://www.esri.com)
[![Python](https://img.shields.io/badge/Python-2.7%20%7C%203.x-yellow)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📌 背景 / Background

**中文**  
在 GIS 日常工作中，CAD/DWG 数据常需批量转为 GIS 格式、统一坐标系、进行拓扑检查。手动操作费时且易错。本工具实现全流程自动化，特别针对**宗地图、规划地块**等对几何精度要求严苛的场景进行了优化。

**English**  
Manual conversion of DWG files to GIS formats is tedious and error-prone. This tool automates the entire pipeline — CAD import, coordinate system assignment, geometry repair, and dynamic topology validation — with special handling for **cadastral/parcel data** where boundary simplification must be avoided.

---

## ⚙️ 核心功能 / Core Features

| 功能模块 Module                 | 说明 (中文)                                                               | Description (EN)                                                         |
|--------------------------------|---------------------------------------------------------------------------|---------------------------------------------------------------------------|
| DWG 有效性预检                 | 自动跳过小于 5KB 的损坏文件。                                             | Skips DWG files < 5KB (corrupted/empty).                                  |
| 坐标系定义                     | 自动生成 `.prj`，固定为 **CGCS2000 (EPSG:4490)**。                         | Writes `.prj` file, fixed to CGCS2000 / EPSG:4490.                        |
| CAD → GDB 转换                 | 调用 `CADToGeodatabase`，保留图层结构，输出至要素数据集。                  | Converts DWG to feature dataset using `CADToGeodatabase`.                 |
| 几何修复                       | `RepairGeometry` 修复微小错误（默认开启）。                                | Repairs invalid geometries (enabled by default).                          |
| 面简化                         | **默认关闭** — 宗地边界不宜简化，防止形状偏移。                            | **Disabled by default** – boundary simplification is unsafe for parcels.  |
| 删除重复要素                   | **默认关闭** — 防止误删合法重叠的地块。                                    | **Disabled by default** – avoids accidental deletion of valid overlaps.   |
| 动态容差拓扑检查               | 从容差 0.0001m 起逐步放大，自动处理 ArcPy 错误 `160342`，强制**面不重叠**。 | Dynamic tolerance retry (0.0001m → 0.05m) handles error `160342`. Enforces **Must Not Overlap**. |
| 双通道日志                     | 控制台实时输出 + `.log` 文件持久化。                                      | Console output + persistent `.log` file.                                  |

---

## 🧠 技术栈 / Tech Stack

- Python (2.7 / 3.x depending on ArcGIS version)
- ArcPy (ArcGIS Desktop / ArcGIS Pro)
- logging, os, re, datetime

---

## 📂 项目结构 / Project Structure

```text
dwg-to-gis-automation/
├── main.py                 # 主脚本 / Main script
├── dwg_process_*.log       # 自动生成的日志 / Auto-generated logs
├── output/                 # 输出目录示例 / Output folder example
│   └── ZongDi_Data.gdb
└── README.md
```

---

## 🚀 快速开始 / Quick Start

### 1. 环境要求 / Requirements

- **ArcGIS Desktop 10.x** or **ArcGIS Pro** (ArcPy required)
- Python environment with ArcPy installed

### 2. 配置脚本 / Configuration

Edit the parameter section at the top of `main.py`:

```python
cad_folder = r"C:/dwg_input"          # DWG 文件夹路径 (supports subfolders)
gdb_path   = r"C:/output"             # 输出 GDB 的父目录 / Parent folder for GDB
gdb_name   = "ZongDi_Data.gdb"        # 输出 GDB 名称 / Output GDB name

sr = arcpy.SpatialReference(4490)     # CGCS2000 (change if needed)
reference_scale = 1000
```

### 3. 调整功能开关 / Feature Toggles

```python
ENABLE_CLEANING      = True   # 修复几何 / Repair geometry
ENABLE_SIMPLIFY      = False  # 简化面 / Simplify polygon (keep False for parcels!)
ENABLE_DELETE_EMPTY  = False  # 删除重复要素 / Delete identical features
ENABLE_TOPOLOGY      = True   # 拓扑检查 / Topology validation
```

### 4. 运行 / Run

```bash
python main.py
```

---

## 🔄 工作流程 / Workflow

```
1. 扫描 DWG 文件 (递归子目录) / Scan DWG recursively
2. 文件大小校验 (<5KB 跳过) / Skip if <5KB
3. 写入同名 .prj 文件 / Write .prj with CGCS2000
4. CADToGeodatabase 转换 / Convert to feature dataset
5. [可选] RepairGeometry 修复 / Repair geometry
6. [可选] 动态容差拓扑验证 / Dynamic topology validation
7. 记录日志 → 下一个文件 / Log and proceed
```

---

## 🧾 日志说明 / Logging

每次运行生成 `dwg_process_YYYYMMDD_HHMMSS.log`。

| 级别 Level | 含义 Meaning                                                  |
|------------|---------------------------------------------------------------|
| INFO       | 正常流程节点 / Normal progress                                 |
| WARNING    | 非致命问题 (文件过小、拓扑容差重试) / Non‑critical issues      |
| ERROR      | 转换失败、拓扑彻底失败 / Critical failure                      |

---

## 🔧 高级配置 / Advanced Settings

### 拓扑规则 / Topology Rules

Modify the dictionary in `main.py`:

```python
TOPOLOGY_RULES = {
    "Must_Not_Overlap": True,       # 面不能重叠 / No polygon overlap
    "Must_Not_Have_Gaps": False,    # 面不能有缝隙 / No gaps
    "Must_Not_Self_Intersect": True # 自相交检查 / No self‑intersection
}
```

### 动态容差序列 / Tolerance Sequence

When ArcPy throws error `160342`, the script retries with larger tolerances:

```python
TOLERANCE_SEQUENCE = [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05]  # meters
```

### 简化面容差 / Simplify Tolerance (reserved)

```python
SIMPLIFY_TOLERANCE = "0.001 Meters"   # Only used if ENABLE_SIMPLIFY = True
```

---

## 💡 输出结构 / Output Structure

```
ZongDi_Data.gdb
├── CAD_<dwg_name_1> (Feature Dataset)
│   ├── Annotation
│   ├── MultiPatch
│   ├── Point
│   ├── Polygon          ← 主要宗地面 / Parcel polygons
│   └── Polyline
├── CAD_<dwg_name_2>
│   └── ...
```

Each DWG gets its own feature dataset prefixed with `CAD_`.

---

## 🐛 常见问题 / Troubleshooting

| 现象 Symptom                                       | 解决方法 Solution                                                                 |
|----------------------------------------------------|-----------------------------------------------------------------------------------|
| `ERROR 000732`: 数据集不存在 / Dataset does not exist | 检查输出路径写入权限或磁盘空间 / Check write permissions and disk space.          |
| `160342`: 拓扑引擎出错 / Topology engine error       | 脚本已内置自动重试。若最终失败，检查源 DWG 几何合法性 / Script retries automatically. If persistent, check source DWG geometry. |
| 转换后要素类为空 / Empty feature class after import  | DWG 中可能仅有块参照而无实体，或 `reference_scale` 过小 / DWG contains only blocks; try increasing reference scale. |
| 控制台中文乱码 / Console encoding issue             | 在 ArcGIS 自带的 Python 窗口运行，或设置系统编码为 UTF-8 / Run inside ArcGIS Python window. |

---

## 🔮 未来改进 / Future Improvements

- [ ] 外部配置文件支持 / External config file (JSON/YAML)
- [ ] 多进程并行 / Parallel processing
- [ ] 按图层名称过滤 / Layer filtering
- [ ] 封装为 ArcGIS Toolbox / Package as ArcGIS toolbox
- [ ] 支持输出 Shapefile / Shapefile export option

---

## 👨‍💻 作者 / Author

**RedBull-coder**  
版本 / Version：企业级最终版 (修复版)  
最后更新 / Last Update：2026.04

> ⚠️ 宗地数据处理请务必保持 `ENABLE_SIMPLIFY = False`，以免边界偏移引发法律纠纷。  
> *For cadastral data, always keep `ENABLE_SIMPLIFY = False` to prevent boundary shifts.*

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
