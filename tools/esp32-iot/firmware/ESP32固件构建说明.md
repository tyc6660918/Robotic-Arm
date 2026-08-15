# Mongoose：嵌入式 Web 服务器与网络协议库

[![License: GPLv2/Commercial](https://img.shields.io/badge/License-GPLv2%20or%20Commercial-green.svg)](https://opensource.org/licenses/gpl-2.0.php)
[![Build Status]( https://github.com/cesanta/mongoose/workflows/build/badge.svg)](https://github.com/cesanta/mongoose/actions)
[![Code Coverage](https://codecov.io/gh/cesanta/mongoose/branch/master/graph/badge.svg)](https://codecov.io/gh/cesanta/mongoose)
[![Fuzzing Status](https://oss-fuzz-build-logs.storage.googleapis.com/badges/mongoose.svg)](https://bugs.chromium.org/p/oss-fuzz/issues/list?sort=-opened&can=1&q=proj:mongoose)

Mongoose 是一款面向 C/C++ 的网络协议库。它为 TCP、UDP、HTTP、WebSocket、MQTT 实现了事件驱动的非阻塞 API。该库旨在将各类设备接入并连接至互联网。Mongoose 自 2004 年上市以来，已被大量开源与商业产品所采用——甚至运行于国际空间站之上！Mongoose 使嵌入式网络编程变得快速、健壮且易于实现。其特性包括：

- 跨平台：
  - 支持 Linux/UNIX、MacOS、Windows、Android
  - 支持 STM32、NXP、ESP32、NRF52、TI、Microchip 等平台
  - 一次编写，随处运行
  - 非常适合在企业范围内统一网络基础设施代码
- 内置协议：纯 TCP/UDP、SNTP、HTTP、MQTT、WebSocket
- SSL/TLS 支持：mbedTLS、OpenSSL 或自定义实现（通过 API）
- 异步 DNS 解析器
- 极小的静态与运行时内存占用
- 源代码同时兼容 ISO C 与 ISO C++ 标准
- 极易集成：只需将 `mongoose.c` 和 `mongoose.h` 文件复制到您的源码树中即可。参见[具体步骤](https://mongoose.ws/documentation/#2-minute-integration-guide)
- 可与任何提供 socket API 的网络协议栈协同工作，如 LwIP 或 FreeRTOS-Plus-TCP
- 内置 TCP/IP 协议栈，并提供面向裸机或 RTOS 系统的驱动
  - 可用驱动：STM32 F4、F7、H5、H7；NXP RT1020；TI TM4C；Microchip SAME54；Wiznet W5500
  - 在裸机平台上完整的 Web 设备仪表板示例 [Nucleo-F429ZI](examples/stm32/nucleo-f429zi-baremetal) 仅包含 6 个文件
  - 相比之下，CubeIDE 生成的 HTTP 示例需要 400 多个文件
- 为 STM32H5、STM32H7 提供内置固件更新功能，更多平台支持即将推出
- 提供详尽的[用户指南、API 参考及大量教程](https://mongoose.ws/documentation/)


# 商业应用

- Mongoose 被数百家企业采用，涵盖财富 500 强巨头（如西门子、施耐德电气、博通、博世、谷歌、三星、高通、卡特彼勒）至各类中小企业
- 广泛应用于解决多样化的业务需求，如在设备上实现 Web UI 界面、RESTful API 服务、遥测数据交换、产品远程控制、远程软件更新、远程监控等
- 已在全球生产环境中部署至数亿台设备
- 参阅我们尊贵客户的[案例研究](https://mongoose.ws/case-studies/)，包括[施耐德电气](https://mongoose.ws/case-studies/schneider-electric/)（工业自动化）、[博通](https://mongoose.ws/case-studies/broadcom/)（半导体）、[Pilz](https://mongoose.ws/case-studies/pilz/)（工业自动化）等
- 参阅已在商业产品中集成 Mongoose 的工程师的[用户评价](https://mongoose.ws/testimonials/)
- 我们提供[评估与商业许可](https://mongoose.ws/licensing/)、[技术支持](https://mongoose.ws/support/)、咨询及[集成服务](https://mongoose.ws/integration/)——欢迎随时[联系我们](https://mongoose.ws/contact/)


# 安全性

我们高度重视安全保障：
1. Mongoose 代码仓库运行由 GitHub 驱动的[持续集成测试](https://github.com/cesanta/mongoose/actions)，对仓库的每一次提交均执行数百项单元测试。我们的[单元测试](https://github.com/cesanta/mongoose/tree/master/test)采用现代地址消毒技术构建，有助于及早发现安全漏洞。
2. Mongoose 代码仓库已接入 Google 的 [oss-fuzz 持续模糊测试系统](https://bugs.chromium.org/p/oss-fuzz/issues/list?sort=-opened&can=1&q=proj:mongoose)，持续扫描潜在漏洞。
3. 我们定期接收来自独立安全团队的漏洞报告，例如 [Cisco Talos](https://www.cisco.com/c/en/us/products/security/talos.html)、[微软安全响应中心](https://www.microsoft.com/en-us/msrc)、[MITRE 公司](https://www.mitre.org/)、[Compass Security](https://www.compass-security.com/en/) 等。一旦发现漏洞，我们将遵循行业最佳实践：暂缓公开披露，修复软件后通知所有具备相应订阅服务的客户。
4. 部分客户（例如 NASA）具有特定的安全要求并执行独立的安全审计；我们会在收到通知后，按照上述第 (3) 条相同的流程处理发现的任何问题。


# 贡献

欢迎贡献代码！请遵循以下准则：

- 签署 [Cesanta CLA](https://cesanta.com/cla.html) 并提交 GitHub Pull Request
- 确保每个 PR 仅包含一个提交，且只处理一个问题
