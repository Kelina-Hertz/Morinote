# AI 运行依赖及许可证

本版本按需启用 AI，不附带模型账户、订阅或 API Key。

| 组件 | 固定来源／版本 | 许可证位置 |
|---|---|---|
| DeepSeek Harness SDK 与 CLI | 官方仓库提交 `22ddee3792402c3e70ec5f86a63c3e3e895a2f60`，0.2.1-rc.3 | `resources/ai-runtime/licenses/DSH-LICENSE`、`DSH-THIRD_PARTY_NOTICES.md` |
| Node.js | 25.8.2，Windows x64 | `resources/ai-runtime/node/LICENSE`，包含 Node 及其依赖声明 |
| PowerShell | 7.6.5，Windows x64 | `resources/ai-runtime/pwsh/LICENSE.txt` 及该目录中的第三方声明 |
| DSH 的 vendored Cordis／Schemastery 等 | 与上述提交共同构建 | 对应包目录的 LICENSE、DSH 第三方声明 |
| Windows FFI／受限执行依赖 | 冻结锁文件中的 Koffi 3.1.1 等 | 对应 `node_modules` 包目录许可证 |

完整包名、版本、来源和许可证索引位于 `resources/ai-runtime/licenses/dependency-inventory.json`。未在每个 workspace 包单独重复的 DSH 授权文本保留在运行目录的 `licenses` 中。发行时请保留这些文件及各依赖自带的版权声明。

上游：[DeepSeek Harness 固定版本](https://github.com/deepseek-ai/deepseek-harness/tree/22ddee3792402c3e70ec5f86a63c3e3e895a2f60)、[Windows 沙箱说明](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/docs/subsystems/sandbox.md)、[Node.js](https://nodejs.org/)、[PowerShell](https://github.com/PowerShell/PowerShell)。
