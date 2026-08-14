# 🚀 STM32 调试快速上手（5分钟）

**环境状态:** ✅ 调试环境已配置完成

---

## 硬件连接（3步）

### Step 1: 连接调试器到电脑
```
CMSIS-DAP (野火 DAP 小智款) → USB 线 → PC
```

### Step 2: 连接调试器到开发板
```
DAP 调试器 → SWD 排线 → 开发板 SWD 接口
  - SWDIO (数据线)
  - SWCLK (时钟线)
  - GND (地线)
  - 3V3 (可选，为目标板供电)
```

### Step 3: 给开发板上电
```
USB 线 → 开发板
或
外部电源 → 开发板电源接口
```

---

## 测试连接

```bash
cd debug/openocd-configs
bash test-connection.sh
```

**预期输出:**
```
✓ OpenOCD 检测到目标
✓ STM32F103ZET6 connected
```

---

## VSCode 一键调试

### 方法 1: 按 F5 快捷键（推荐）
1. 在 VSCode 中打开项目
2. 按 `F5` 键
3. 选择调试配置（如 "Debug rst-control (DAP)"）
4. 等待自动编译 → 烧录 → 启动调试

### 方法 2: 使用调试面板
1. 点击左侧调试图标（虫子图标）
2. 在下拉菜单选择调试配置
3. 点击绿色播放按钮

---

## 可用的调试配置

### Dummy 从臂固件（8个配置）
```
- Debug rst-control (DAP)          # 主控制器 + DAP
- Debug rst-control (ST-Link)      # 主控制器 + ST-Link
- Debug dummy-35motor (DAP)        # 35电机驱动 + DAP
- Debug dummy-35motor (ST-Link)    # 35电机驱动 + ST-Link
- Debug dummy-42motor (DAP)        # 42电机驱动 + DAP
- Debug dummy-42motor (ST-Link)    # 42电机驱动 + ST-Link
- Debug dummy-ref-core (DAP)       # 参考控制器 + DAP
- Debug dummy-ref-core (ST-Link)   # 参考控制器 + ST-Link
```

---

## 常见问题

### Q: OpenOCD 无法连接
**A:** 检查：
1. DAP 驱动是否已安装
2. SWD 线是否连接正确（特别是 GND）
3. 开发板是否上电
4. USB 设备管理器中是否能看到 DAP 设备

### Q: 按 F5 后编译失败
**A:** 确保已安装：
- arm-none-eabi-gcc 工具链
- make 工具

### Q: 烧录成功但程序不运行
**A:** 检查：
1. 开发板 BOOT0 跳线是否正确（应该接 GND）
2. 复位后重新连接调试器
3. 查看串口输出（115200 波特率）

---

## 命令行调试（可选）

如果不想用 VSCode，也可以手动启动：

```bash
# 终端 1: 启动 OpenOCD
cd debug/openocd-configs
openocd -f cmsis-dap-f103.cfg

# 终端 2: 启动 GDB
cd robots/dummy-arm/firmware/stm32-control
arm-none-eabi-gdb build/control.elf
(gdb) target remote :3333
(gdb) load
(gdb) continue
```

---

## 下一步

- 📖 完整调试教程 → [`../guides/debugging-complete.md`](../guides/debugging-complete.md)
- 🔄 开发工作流 → [`workflow.md`](workflow.md)
- 🤖 Claude AI 远程调试 → [`../guides/claude-debug.md`](../guides/claude-debug.md)

---

**遇到问题？把错误信息告诉我，我帮你分析！** 💬
