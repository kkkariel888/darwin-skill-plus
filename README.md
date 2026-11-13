# 达尔文增强版 Darwin Skill Plus

基于花叔的 [darwin-skill](https://github.com/alchaincyf/darwin-skill)（MIT）修改。达尔文的打分、优化、盲评、保留或撤回这一整套都和原版一样，增强版多做了一件事：

**优化完，顺手检查这个 skill 发出去以后，用户能不能自动收到更新。**

- 检查 skill 所在仓库是不是插件市场结构（不是的话，用户只能手动复制，永远收不到更新）
- 优化改了内容 → 提醒你涨版本号，你点头就一键改齐（不涨版本号，用户那边就当没有新版本）
- 其他缺的（README 没教开自动更新、没有 GitHub 自动检查）写进报告，可以用 [ariel-release-check](https://github.com/kkkariel888/ariel-release-check) 一次补齐
- 优化记录放在 `~/.darwin-skill-plus/`，插件自己更新时不会丢

装好后对 AI 说：「用达尔文优化一下 XX skill」或「用达尔文给我所有 skill 打个分」。

## 安装（装一次，以后作者更新会自动到你手里）

**最省事：让 AI 帮你装**
把这句话发给 Claude 或 Codex：「帮我安装插件市场 kkkariel888/darwin-skill-plus 里的 darwin-skill-plus，并打开自动更新」

**Claude 桌面 app / 网页版**
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
