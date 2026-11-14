# README 安装段模板（放在 README 靠前的位置）

把 `<...>` 换掉。顺序就是推荐顺序：越往上越省事、越能自动更新。

```markdown
## 安装（装一次，以后作者更新会自动到你手里）

**最省事：让 AI 帮你装**
把这句话发给 Claude 或 Codex：「帮我安装插件市场 <GitHub 用户名>/<仓库名> 里的 <插件名>，并打开自动更新」

**Claude 桌面 app / 网页版**
Customize → Plugins → Add → Add marketplace → Add from a repository → 填 `<GitHub 用户名>/<仓库名>` → 打开 **Sync automatically** → 装 <插件名>

**Claude Code**
/plugin marketplace add <GitHub 用户名>/<仓库名>
/plugin install <插件名>@<市场名>
装完打开自动更新：`/plugin` → Marketplaces → 选 <市场名> → Enable auto-update（第三方市场默认是关的）

**Codex**
codex plugin marketplace add <GitHub 用户名>/<仓库名>
codex plugin add <插件名>@<市场名>

> ⚠️ 直接下载 zip、手动把文件复制进 skills 文件夹也能用，但**不会自动更新**，以后要自己重新下载。
```
