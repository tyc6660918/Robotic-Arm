#!/bin/bash

# OpenOCD 硬件连接测试脚本
# 用于自动检测调试器和目标芯片

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENOCD_BIN="/c/Users/TYC/.embedded-tools/openocd/xpack-openocd-0.12.0-7/bin/openocd"

echo "=========================================="
echo "OpenOCD 硬件连接测试"
echo "=========================================="
echo

# 检查 OpenOCD 是否存在
if [ ! -f "$OPENOCD_BIN" ]; then
    echo "❌ 错误: OpenOCD 未找到"
    echo "路径: $OPENOCD_BIN"
    exit 1
fi

echo "✅ OpenOCD 已安装"
"$OPENOCD_BIN" --version | head -1
echo

# 测试配置文件列表
declare -A CONFIGS
CONFIGS=(
    ["ST-Link + STM32F103"]="$SCRIPT_DIR/stlink-f103.cfg"
    ["CMSIS-DAP + STM32F103"]="$SCRIPT_DIR/cmsis-dap-f103.cfg"
    ["WCH-Link + STM32F103"]="$SCRIPT_DIR/wch-link-f103.cfg"
    ["ST-Link + STM32F405"]="$SCRIPT_DIR/stlink-f405.cfg"
)

echo "=========================================="
echo "可用的配置文件:"
echo "=========================================="
for name in "${!CONFIGS[@]}"; do
    cfg="${CONFIGS[$name]}"
    if [ -f "$cfg" ]; then
        echo "  ✅ $name"
    else
        echo "  ❌ $name (文件不存在)"
    fi
done
echo

# 测试每个配置
echo "=========================================="
echo "开始测试硬件连接..."
echo "=========================================="
echo

SUCCESS_COUNT=0
TESTED_COUNT=0

for name in "${!CONFIGS[@]}"; do
    cfg="${CONFIGS[$name]}"

    if [ ! -f "$cfg" ]; then
        continue
    fi

    TESTED_COUNT=$((TESTED_COUNT + 1))

    echo "---"
    echo "测试: $name"
    echo "配置: $(basename "$cfg")"
    echo

    # 尝试连接（超时 3 秒）
    if timeout 3 "$OPENOCD_BIN" -f "$cfg" -c init -c exit 2>&1 | tee /tmp/openocd_test.log | grep -q "Info.*Listening on port"; then
        echo "✅ 成功连接!"
        echo
        echo "连接详情:"
        grep -E "Info.*voltage|Info.*hardware|Info.*Listening" /tmp/openocd_test.log | sed 's/^/  /'
        echo
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))

        # 保存成功的配置
        echo "$cfg" > /tmp/openocd_working_config.txt
    else
        echo "❌ 连接失败"
        echo
        echo "错误信息:"
        grep -E "Error|Warn" /tmp/openocd_test.log | head -5 | sed 's/^/  /'
        echo
    fi

    sleep 1
done

echo "=========================================="
echo "测试总结"
echo "=========================================="
echo "测试配置数: $TESTED_COUNT"
echo "成功连接数: $SUCCESS_COUNT"
echo

if [ $SUCCESS_COUNT -eq 0 ]; then
    echo "❌ 所有配置均连接失败"
    echo
    echo "可能的原因:"
    echo "  1. 调试器未连接到电脑"
    echo "  2. 目标板未上电"
    echo "  3. SWD/JTAG 连接线松动"
    echo "  4. 驱动未正确安装"
    echo "  5. 设备被其他程序占用"
    echo
    echo "建议:"
    echo "  1. 检查硬件连接"
    echo "  2. 确认设备管理器中识别了调试器"
    echo "  3. 尝试断开重连调试器"
    echo "  4. 查看 README.md 中的故障排除部分"
    exit 1
elif [ $SUCCESS_COUNT -eq 1 ]; then
    WORKING_CFG=$(cat /tmp/openocd_working_config.txt)
    echo "✅ 找到可用配置:"
    echo "   $(basename "$WORKING_CFG")"
    echo
    echo "后续使用方法:"
    echo "  # 烧录固件"
    echo "  openocd -f $WORKING_CFG -c \"program firmware.elf verify reset exit\""
    echo
    echo "  # 启动调试服务器"
    echo "  openocd -f $WORKING_CFG"
    echo
else
    echo "✅ 找到 $SUCCESS_COUNT 个可用配置"
    echo
    echo "建议使用第一个成功的配置进行开发"
fi

echo "=========================================="
echo "测试完成"
echo "=========================================="
