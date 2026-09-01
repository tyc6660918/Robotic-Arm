#!/bin/bash
# 文档优化脚本 - OpenRST项目
# 日期：2026-09-01
# 目的：清理冗余、统一中文命名

cd "$(dirname "$0")"

echo "开始文档优化..."

# ============================================
# 阶段1: 删除冗余文档（5个）
# ============================================
echo ""
echo "阶段1: 删除冗余文档..."

rm -f "MG310P20更新完成.txt"
echo "  ✓ 删除：MG310P20更新完成.txt"

rm -f "MG310P20机械设计完成.txt"
echo "  ✓ 删除：MG310P20机械设计完成.txt"

rm -f "目录结构.txt"
echo "  ✓ 删除：目录结构.txt"

rm -f "工作总结.md"
echo "  ✓ 删除：工作总结.md"

rm -f "任务完成报告.md"
echo "  ✓ 删除：任务完成报告.md"

# ============================================
# 阶段2: 重命名英文文档为中文（9个）
# ============================================
echo ""
echo "阶段2: 重命名英文文档为中文..."

cd 03_设计方案文档

mv "MG310P20_QUICK_START.md" "MG310P20快速入门.md" 2>/dev/null
echo "  ✓ 重命名：MG310P20_QUICK_START.md → MG310P20快速入门.md"

mv "MG310P20_UPDATE_SUMMARY.md" "MG310P20更新摘要.md" 2>/dev/null
echo "  ✓ 重命名：MG310P20_UPDATE_SUMMARY.md → MG310P20更新摘要.md"

mv "MG310P20_MECHANICAL_DESIGN.md" "MG310P20机械设计方案.md" 2>/dev/null
echo "  ✓ 重命名：MG310P20_MECHANICAL_DESIGN.md → MG310P20机械设计方案.md"

mv "MG310P20_REDESIGN_CHECKLIST.md" "MG310P20重新设计清单.md" 2>/dev/null
echo "  ✓ 重命名：MG310P20_REDESIGN_CHECKLIST.md → MG310P20重新设计清单.md"

mv "MG310P20_UPDATE_PLAN.md" "MG310P20电机更新计划.md" 2>/dev/null
echo "  ✓ 重命名：MG310P20_UPDATE_PLAN.md → MG310P20电机更新计划.md"

mv "MG310P20_DOCUMENT_INDEX.md" "MG310P20文档索引.md" 2>/dev/null
echo "  ✓ 重命名：MG310P20_DOCUMENT_INDEX.md → MG310P20文档索引.md"

mv "MG310P20_COMPLETION_REPORT.md" "MG310P20完成报告.md" 2>/dev/null
echo "  ✓ 重命名：MG310P20_COMPLETION_REPORT.md → MG310P20完成报告.md"

mv "MOTOR_CHANGE_PLAN.md" "电机更换初步方案.md" 2>/dev/null
echo "  ✓ 重命名：MOTOR_CHANGE_PLAN.md → 电机更换初步方案.md"

mv "REDESIGN_PLAN.md" "完整重新设计方案.md" 2>/dev/null
echo "  ✓ 重命名：REDESIGN_PLAN.md → 完整重新设计方案.md"

cd ..

# ============================================
# 阶段3: 删除子目录中的重复README
# ============================================
echo ""
echo "阶段3: 删除重复导航文档..."

rm -f "05_结构分析报告/README.md"
echo "  ✓ 删除：05_结构分析报告/README.md (内容已合并到主README)"

# ============================================
# 完成统计
# ============================================
echo ""
echo "============================================"
echo "✅ 文档优化完成！"
echo "============================================"
echo ""
echo "优化结果："
echo "  • 删除冗余文档：5个"
echo "  • 删除重复导航：1个"
echo "  • 重命名为中文：9个"
echo "  • 总计减少文件：6个"
echo ""
echo "当前文档统计："
find . -type f \( -name "*.md" -o -name "*.txt" \) | wc -l | xargs echo "  • 文档总数："
echo ""
echo "下一步："
echo "  1. 检查文件列表: ls -R"
echo "  2. 提交更改: git add -A && git commit"
echo ""
