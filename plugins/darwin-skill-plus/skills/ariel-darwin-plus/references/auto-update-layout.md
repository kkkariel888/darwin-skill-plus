# 插件市场仓库结构（Claude + Codex 都能装、都能自动更新）

照 kkkariel888/ariel-broll-video 的结构，已实际验证过。`<市场名>` 一般就是仓库名，`<插件名>` 是 skill 名。

```
<仓库>/
├── .claude-plugin/marketplace.json        Claude 的市场清单
├── .agents/plugins/marketplace.json       Codex 的市场清单
├── plugins/<插件名>/
│   ├── .claude-plugin/plugin.json         Claude 插件身份证（version 以这里为准）
│   ├── .codex-plugin/plugin.json          Codex 插件身份证（version 和上面一样）
│   └── skills/<插件名>/SKILL.md           skill 本体（必须在这一层，放插件根目录 Claude 找不到）
│       └── scripts/update_check.py        开工查新版本：有新版这次就直接用新版
├── tools/bump.py                          一键改齐版本号
├── tools/check_version_bump.py            GitHub 自动检查用
├── .github/workflows/version-check.yml    忘涨版本号就拦下合并
├── README.md                              首推插件市场装法
└── LICENSE
```

## .claude-plugin/marketplace.json
```json
{
  "name": "<市场名>",
  "owner": {"name": "<GitHub 用户名>"},
  "metadata": {"description": "一句话：装一次，作者更新自动到你手里"},
  "plugins": [
    {"name": "<插件名>", "source": "./plugins/<插件名>", "description": "做什么", "version": "1.0.0"}
  ]
}
```

## plugins/<插件名>/.claude-plugin/plugin.json
```json
{"name": "<插件名>", "version": "1.0.0", "description": "做什么", "author": {"name": "<GitHub 用户名>"}, "license": "MIT"}
```

## .agents/plugins/marketplace.json（Codex）
```json
{
  "name": "<市场名>",
  "interface": {"displayName": "<中文显示名>"},
  "plugins": [
    {"name": "<插件名>", "source": {"source": "local", "path": "./plugins/<插件名>"},
     "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"}
  ]
}
```

## plugins/<插件名>/.codex-plugin/plugin.json
```json
{"name": "<插件名>", "version": "1.0.0", "description": "做什么", "skills": "./skills",
 "interface": {"displayName": "<中文显示名>", "shortDescription": "一句话", "developerName": "<GitHub 用户名>", "category": "Productivity"}}
```

## 版本号规矩
- 三处 version（marketplace 条目、Claude plugin.json、Codex plugin.json）永远一样，用 `tools/bump.py` 改，不手改。
- **plugin.json 的 version 优先级最高**：只改 marketplace 不改 plugin.json，等于没改。
- 每次用户能感觉到的改动（SKILL.md、脚本、资源）都要涨版本号。不涨 = 用户收不到。
- 只改 README、tools/、.github/ 不用涨。
- 本地目录装的插件会实时读文件，**看不出漏涨版本号**；要验证就用 GitHub 上的市场装一次。
