#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档优化脚本 - OpenRST项目
日期：2026-09-01
目的：清理冗余、统一中文命名
"""

import os
import shutil
from pathlib import Path

def main():
    # 获取脚本所在目录
    base_dir = Path(__file__).parent
    os.chdir(base_dir)

    print("开始文档优化...")
    print(f"工作目录: {base_dir}")

    # ============================================
    # 阶段1: 删除冗余文档（5个）
    # ============================================
    print("\n" + "="*50)
    print("阶段1: 删除冗余文档...")
    print("="*50)

    files_to_delete = [
        "MG310P20更新完成.txt",
        "MG310P20机械设计完成.txt",
        "目录结构.txt",
        "工作总结.md",
        "任务完成报告.md"
    ]

    deleted_count = 0
    for filename in files_to_delete:
        filepath = base_dir / filename
        if filepath.exists():
            filepath.unlink()
            print(f"  ✓ 删除：{filename}")
            deleted_count += 1
        else:
            print(f"  ⊘ 跳过：{filename} (不存在)")

    # ============================================
    # 阶段2: 重命名英文文档为中文（9个）
    # ============================================
    print("\n" + "="*50)
    print("阶段2: 重命名英文文档为中文...")
    print("="*50)

    rename_map = {
        "03_设计方案文档/MG310P20_QUICK_START.md": "03_设计方案文档/MG310P20快速入门.md",
        "03_设计方案文档/MG310P20_UPDATE_SUMMARY.md": "03_设计方案文档/MG310P20更新摘要.md",
        "03_设计方案文档/MG310P20_MECHANICAL_DESIGN.md": "03_设计方案文档/MG310P20机械设计方案.md",
        "03_设计方案文档/MG310P20_REDESIGN_CHECKLIST.md": "03_设计方案文档/MG310P20重新设计清单.md",
        "03_设计方案文档/MG310P20_UPDATE_PLAN.md": "03_设计方案文档/MG310P20电机更新计划.md",
        "03_设计方案文档/MG310P20_DOCUMENT_INDEX.md": "03_设计方案文档/MG310P20文档索引.md",
        "03_设计方案文档/MG310P20_COMPLETION_REPORT.md": "03_设计方案文档/MG310P20完成报告.md",
        "03_设计方案文档/MOTOR_CHANGE_PLAN.md": "03_设计方案文档/电机更换初步方案.md",
        "03_设计方案文档/REDESIGN_PLAN.md": "03_设计方案文档/完整重新设计方案.md",
    }

    renamed_count = 0
    for old_path, new_path in rename_map.items():
        old_file = base_dir / old_path
        new_file = base_dir / new_path
        if old_file.exists():
            old_file.rename(new_file)
            old_name = old_path.split('/')[-1]
            new_name = new_path.split('/')[-1]
            print(f"  ✓ 重命名：{old_name} → {new_name}")
            renamed_count += 1
        else:
            print(f"  ⊘ 跳过：{old_path} (不存在)")

    # ============================================
    # 阶段3: 删除子目录中的重复README
    # ============================================
    print("\n" + "="*50)
    print("阶段3: 删除重复导航文档...")
    print("="*50)

    readme_to_delete = base_dir / "05_结构分析报告/README.md"
    if readme_to_delete.exists():
        readme_to_delete.unlink()
        print("  ✓ 删除：05_结构分析报告/README.md (内容已合并到主README)")
        deleted_count += 1
    else:
        print("  ⊘ 跳过：05_结构分析报告/README.md (不存在)")

    # ============================================
    # 完成统计
    # ============================================
    print("\n" + "="*50)
    print("✅ 文档优化完成！")
    print("="*50)

    # 统计当前文档数量
    md_files = list(base_dir.rglob("*.md"))
    txt_files = list(base_dir.rglob("*.txt"))
    total_docs = len(md_files) + len(txt_files)

    print(f"\n优化结果：")
    print(f"  • 删除冗余文档：{deleted_count}个")
    print(f"  • 重命名为中文：{renamed_count}个")
    print(f"  • 总计减少文件：{deleted_count}个")
    print(f"\n当前文档统计：")
    print(f"  • Markdown文档：{len(md_files)}个")
    print(f"  • 文本文档：{len(txt_files)}个")
    print(f"  • 文档总数：{total_docs}个")

    print("\n文档列表：")
    all_docs = sorted([str(f.relative_to(base_dir)) for f in md_files + txt_files])
    for doc in all_docs:
        print(f"  - {doc}")

    print("\n✨ 完成！所有文档已统一为中文命名。")

if __name__ == "__main__":
    main()
