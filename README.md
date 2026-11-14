# 达尔文增强版 Darwin Skill Plus

基于花叔的 [darwin-skill](https://github.com/alchaincyf/darwin-skill)（MIT）修改。达尔文的打分、优化、盲评、保留或撤回这一整套都和原版一样，增强版多做了两件事：

1. **优化完，直接把发布准备做完：体检 + 缺的补齐 + 涨版本号，让用户能自动收到这次优化。**
2. **查 skill 在你要的平台上能不能真跑起来**：Claude Code 终端、Claude 桌面 app、Cowork、Codex。

- 自动检查 skill 所在仓库能不能让用户「装一次、自动更新」
- 缺的自动补上：一键改版本号工具、GitHub 自动检查（忘涨版本号就拦下合并）、开工查新版本（有新版这次就直接用新版）、README 安装和自动更新说明；还不是插件市场结构的，自动搭好
- 改了内容自动涨版本号（比如 1.1.2 → 1.1.3）
- 只在推送到 GitHub 前问你一次（公开操作，推出去收不回），你点「推送」就开合并申请
- 优化记录放在 `~/.darwin-skill-plus/`，插件自己更新时不会丢

**平台适配体检**（默认查 4 个平台，你只要其中几个就跟 AI 说）
- 装得上吗：Claude 插件市场、Codex 插件市场结构齐不齐
- 跑得起来吗：有没有只在 Mac 能用又没退路的命令、要不要显卡、第三方依赖会不会自动装、下载源在 Cowork 会不会被拦、会不会去写沙盒碰不到的桌面
- 卡住时会说人话吗：网络被拦时有没有告诉用户放开哪个网址；要打开网页让用户点的，每个平台怎么打开有没有写
- 还会给每个沙盒平台编一个「环境模拟」测试，跟改前比是不是真的更好
- 有 ❌ 就先修再优化别的；报告里老实列出哪些平台还没真机跑过，不会说「全平台可用」

装好后在对话框打 **`/ariel`** 就能找到它（`ariel-darwin-plus`），或者直接对 AI 说：「用达尔文优化一下 XX skill」或「用达尔文给我所有 skill 打个分」。

## 安装（装一次，以后作者更新会自动到你手里）

**最省事：让 AI 帮你装**
把这句话发给 Claude 或 Codex：「帮我安装插件市场 kkkariel888/darwin-skill-plus 里的 darwin-skill-plus，并打开自动更新」

**Claude 桌面 app（Code 页面和 Cowork 都能用）/ 网页版**
Customize → Plugins → Add → Add marketplace → Add from a repository → 填 `kkkariel888/darwin-skill-plus` → 打开 **Sync automatically** → 装 darwin-skill-plus

**Claude Code**
```
/plugin marketplace add kkkariel888/darwin-skill-plus
/plugin install darwin-skill-plus@darwin-skill-plus
```
装完打开自动更新：`/plugin` → Marketplaces → 选 darwin-skill-plus → Enable auto-update（第三方市场默认是关的）

**Codex**
```bash
codex plugin marketplace add kkkariel888/darwin-skill-plus
codex plugin add darwin-skill-plus@darwin-skill-plus
```

> ⚠️ 直接下载 zip、手动把文件复制进 skills 文件夹也能用，但**不会自动更新**。

## 发新版本（给维护者）
改完后跑 `python3 tools/bump.py`（最后一位 +1），再提合并申请。忘了跑，GitHub 上的 version-check 会亮红灯。

## 致谢与许可证
- 原版：[alchaincyf/darwin-skill](https://github.com/alchaincyf/darwin-skill) by 花叔，MIT。本仓库保留原版 LICENSE 和版权声明。
- 原版的学术依据：SkillLens（arXiv 2605.23899）、SkillOpt（arXiv 2605.23904）、Karpathy autoresearch。
- 本仓库不是花叔官方版本。
- MIT
