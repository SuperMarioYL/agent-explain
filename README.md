[English](README.en.md) | **简体中文**

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/hero-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/hero-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/hero-dark.svg">
  <img src="assets/presentation/hero-light.svg" width="960" alt="agent-explain — Inspect the plan before execution.">
</picture>

**agent-explain 把 Markdown 编码计划拆成逐步投影，在执行前列出 token 估算范围、动作词计数、风险标签和引用文件。**

`Python 3.12+` · [MIT](LICENSE) · [GitHub](https://github.com/SuperMarioYL/agent-explain) · [网站](https://agent-explain.lei6393.com)

## 为什么需要它

审批一份计划时，读文件、改代码和删除配置值得分开看。工具先整理这些动作及其估算依据，帮助你定位需要追问的步骤。它分析计划文字，不执行其中的命令。

自带三步例子覆盖 Read、Edit、Delete。结果分别是 low、medium、high；auth.py 保持原样。

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/process-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/process-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/process-dark.svg">
  <img src="assets/presentation/process-light.svg" width="960" alt="Review three planned actions">
</picture>

## 架构

`parser.py` 按编号标题、编号列表、段落的顺序尝试拆步，提取动作词与文件路径。`analyzer.py` 组合 token 估算和风险规则，`projector.py` 汇总 token 上下限、风险分布及去重后的路径。`renderer.py` 输出表格或 JSON。

CLI 将计划文件目录传入采样器；路径先相对该目录解析，再尝试原路径。目录不作为常规文件采样。

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/architecture-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/architecture-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/architecture-dark.svg">
  <img src="assets/presentation/architecture-light.svg" width="960" alt="Markdown to a reviewable projection">
</picture>

## 安装

需要 Python 3.12+。从源码安装可同时取得示例：

```bash
git clone https://github.com/SuperMarioYL/agent-explain.git
cd agent-explain
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

安装和首次 tokenizer 初始化可能下载资源。不需要模型 API key。

## 快速开始

仓库已提供 `examples/presentation/plan.md` 与其引用的 `auth.py`：

```bash
cat examples/presentation/plan.md
bash docs/demo.sh
```

实际 JSON 总量：`est_tokens_range=[15,60]`，`total_tool_calls=3`，`total_files_touched=2`。前两步为 sampled，删除步骤为 static。不存在的 obsolete.json 只是计划中的路径，不会被创建或删除。

## 用法

```bash
agent-explain explain examples/plan.md
agent-explain explain examples/plan.md --json
agent-explain explain examples/plan.md --json | jq .totals
agent-explain explain examples/plan.md --json | jq '.steps[] | select(.risk_class == "high")'
agent-explain --version
```

v0.6.0 的实际命令需要 `explain` 子命令。JSON 可以作为你自己的审批程序输入；仓库不包含名为 pre-approval-gate 的可执行文件。

## 能力与集成

| 环节 | 提供的能力 |
|---|---|
| Markdown 计划 | 编号标题、列表与段落解析 |
| 本地文件 | 常规文件大小参与估算 |
| 终端阅读 | Rich 逐步表格 |
| 外部审批程序 | JSON 投影；审批策略由接入方负责 |

<picture>
  <source media="(max-width: 640px) and (prefers-color-scheme: dark)" srcset="assets/presentation/integrations-mobile-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/presentation/integrations-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/presentation/integrations-dark.svg">
  <img src="assets/presentation/integrations-light.svg" width="960" alt="Inputs and review outputs">
</picture>

## 配置与边界

当前没有模型或服务配置。token 文本使用 tiktoken；文件估算采用每 4 字节约 1 token。sampled 上限乘数为 1.6，static 为 2.0；confidence 分别固定为 0.70 和 0.40。

这些数值是实现里的启发式，不是统计置信区间。`tool_call_count` 是不同动作词数量。英文关键词中最危险的规则胜出；未匹配的内容默认 low，不能据此认定中文或未知动作安全。

## 运行记录

[完整输入与实际输出](docs/demo-results.json) · [复现脚本](docs/demo.sh)

[历史终端录屏](assets/demo.gif) 与 [录制脚本](docs/demo.tape) 保留供参考。录屏未因本轮文档更新重新录制；当前语法和结果以以上可重放 JSON 示例为准。

## 路线图

- [x] Markdown 步骤、动作词和路径解析。
- [x] 启发式 token 范围、风险规则与文件采样。
- [x] 表格和 JSON 输出、路径去重与总量聚合。
- [ ] 用真实执行数据校准估算。
- [ ] 更多 Agent 原生计划格式、IDE/MCP 接入。

未勾选项不是当前功能。

## 开发与许可证

```bash
python -m pip install pytest
python -m pytest
```

[MIT](LICENSE) · [Issues](https://github.com/SuperMarioYL/agent-explain/issues)
