# 🎯 STM32 调试环境 - 快速启动指南

**5 分钟快速上手** | 适合第一次使用

---

## ⚡ 3 步开始

### 1️⃣ 连接硬件（1 分钟）

```
调试器 ----USB----> 电脑
   |
   | (SWD 线)
   |
   ↓
STM32 开发板 (已上电)
```

**最小连接（必须）:**
- SWDIO → SWDIO (PA13)
- SWCLK → SWCLK (PA14)
- GND → GND

### 2️⃣ 测试连接（30 秒）

打开终端，运行：

```bash
cd /e/Robotic-Arm
bash openocd-configs/test-connection.sh
```

**看到这个就成功了：** ✅ `成功连接!`

### 3️⃣ 开始调试（VSCode，3 分钟）

1. 打开 VSCode
2. 打开文件：`rst-control-fw/control/Core/Src/main.c`
3. 在第 100 行左侧点击，设置断点（出现红点）
4. 按键盘 `F5`
5. 选择 "🐛 rst-control-fw (ST-Link)" 或你的调试器类型
6. 等待编译和烧录（约 30 秒）
7. 程序停在断点处 ✅

**调试快捷键：**
- `F5` - 继续运行
- `F10` - 下一行（不进入函数）
- `F11` - 进入函数
- `Shift+F5` - 停止

---

## 🆘 遇到问题？

### 问题 1: `test-connection.sh` 报错

**解决：**
```bash
# 检查 OpenOCD 是否安装
/c/Users/TYC/.embedded-tools/openocd/xpack-openocd-0.12.0-7/bin/openocd --version

# 如果找不到，检查路径
ls /c/Users/TYC/.embedded-tools/openocd/
```

### 问题 2: 所有配置都连接失败

**可能原因：**
1. 调试器没插好 → 重新插拔 USB
2. 开发板没上电 → 检查电源指示灯
3. SWD 线松动 → 检查 SWDIO/SWCLK/GND 连接
4. 驱动问题 → 打开设备管理器，查看是否识别调试器

### 问题 3: VSCode 按 F5 没反应

**解决：**
1. 检查是否安装了 "Cortex-Debug" 扩展
2. 按 `Ctrl+Shift+P`，输入 "Extensions: Show Recommended Extensions"
3. 安装所有推荐的扩展

---

## 📞 获取 Claude 帮助

**当程序不工作时：**

1. 打开第二个终端：
```bash
cd rst-control-fw/control/build
arm-none-eabi-gdb control.elf
```

2. 在 GDB 中：
```bash
(gdb) target extended-remote localhost:3333
(gdb) monitor reset halt
(gdb) backtrace
(gdb) info registers
```

3. **把所有输出复制，发给 Claude**

4. Claude 会告诉你：
   - 问题在哪里
   - 为什么会这样
   - 如何修复（具体代码）

---

## 📚 详细文档

- **完整调试教程**: `docs/DEBUGGING_GUIDE.md` (658 行)
- **OpenOCD 配置**: `openocd-configs/README.md` (286 行)
- **Claude 协助指南**: `docs/CLAUDE_REMOTE_DEBUG.md` (498 行)
- **完成报告**: `docs/DEBUG_SETUP_COMPLETE.md` (本次配置的所有内容)

---

## ✅ 检查清单

完成这些步骤，你就可以开始开发了：

- [ ] 硬件已连接（调试器 + 开发板）
- [ ] `test-connection.sh` 显示"成功连接"
- [ ] VSCode 能够编译项目（`Ctrl+Shift+B`）
- [ ] VSCode 能够调试（`F5`）
- [ ] 已阅读 `docs/DEBUGGING_GUIDE.md` 快速开始部分

---

**完成了？开始做你的项目吧！** 🎉

**遇到问题？** 把 GDB 输出发给我！
