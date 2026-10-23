# CastoriceWish · Releases

本仓库是 **CastoriceWish**（原神 / 崩坏：星穹铁道 Windows 抽卡记录工具）的**公开发行渠道**，只提供经过确认的发行版本与使用说明，不存放开发源代码。

## 下载和升级

- 前往 [Releases](https://github.com/sirarikako/CastoriceWish.Releases/releases) 下载最新的稳定版。
- **CastoriceWish-Portable.exe**：Windows x64 便携版，无需安装；运行环境需要 Microsoft WebView2 Runtime。
- **CastoriceWish-Portable.zip**：包含便携版和使用说明等附属文件。
- 升级时仅替换 EXE，**保留其同级的 `CastoriceWish_Data` 文件夹**。请先关闭旧版本，不要同时使用多个版本访问同一份数据。

## 版本和安全

每个正式版本以 `vX.Y.Z` Tag 发布；下载前可参考 Release 的更新说明和 SHA-256 校验文件。程序的自动更新功能仍在开发中，**不要将校验哈希误认为数字签名**。发布前由开发仓库完成构建和验证，本仓库仅分发已生成的文件。

本仓库不需要用户提供 GitHub Token。不要在 Issue、讨论或反馈中发布抽卡授权链接、私人 Token、个人账号档案或其他敏感信息。

## 发布仓库的边界

- `main` 仅维护本说明等轻量公共文档；正式安装文件作为 GitHub Release Assets 发布，**不提交到 Git 历史**。
- 不包含私有开发仓库的源代码、构建源文件列表、开发者密钥、日志和测试档案。
- 测试版与诊断版不得标为正式的 Latest Release。
