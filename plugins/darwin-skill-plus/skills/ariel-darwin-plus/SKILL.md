---
name: ariel-darwin-plus
description: "Darwin Skill Plus（达尔文增强版，基于花叔 darwin-skill 2.1，MIT）: 在原版基础上加了「自动发布准备」——优化完自动检查并补齐 skill 所在仓库的自动更新结构、自动涨版本号，推送前问一次；和「平台适配体检」——查 skill 在开发者要的 AI 里能不能完整用（默认 Claude 桌面 app 的 Code 页面 + Codex，点名的其他 AI 照官方规范补上），装不上、跑不起来的当 P0 改好；和「真实体验关」——复杂项目先写体验剧本，再真跑一遍按体验标准（多久有反馈、点了有没有反应、用户要点几下、文件夹干不干净）打分，不达标当 P0 修。Autonomous skill optimizer, v2.0 integrates Microsoft Research SkillLens (arXiv 2605.23899) 9-dim rubric + SkillOpt (arXiv 2605.23904) validation-gated design + human-in-the-loop checkpoints. Evaluates SKILL.md files using a 9-dimension rubric (structure + effectiveness + meta-skill blacklists), runs hill-climbing with git version control, spawns independent judge agents for blind evaluation, validates improvements through test prompts with auto-break on diminishing returns, and generates visual result cards. Use when user mentions \"优化skill\", \"skill评分\", \"自动优化\", \"auto optimize\", \"skill质量检查\", \"达尔文\", \"darwin\", \"帮我改改skill\", \"skill怎么样\", \"提升skill质量\", \"skill review\", \"skill打分\", \"达尔文增强版\", \"darwin plus\", \"能不能自动更新\", \"平台适配\", \"能不能在 Cowork 用\", \"Codex 能不能用\", \"全平台\", \"体验测试\", \"真跑一遍\", \"用户体验\", \"好不好用\", \"太慢\"."
---

# Darwin Skill Plus（达尔文增强版）

> **Plus · 2026-11-13** — fork 自花叔 [darwin-skill](https://github.com/alchaincyf/darwin-skill)（MIT）。新增「自动发布准备」（优化完自动体检 + 补齐 + 涨版本号，见下方同名章节）、results.tsv 挪到 `~/.darwin-skill-plus/`（插件更新不丢历史）、开工自查新版本。其余规则与原版一致。
> `<本skill>` 指这份 SKILL.md 所在的文件夹。

> **v2.1 · 2026-06-10** — keep/revert 棘轮从「绝对分数 delta」改为「**paired 同-judge 比较 + 奇数 N 多数决**」（绝对分数 ±8 judge 噪音淹没保守编辑的真实增益、是 false-revert 源；within-judge 比较消除换尺污染）。绝对分数降级为 triage-only。
> **v2.0 · 2026-05-28** — 吸收 Microsoft Research SkillLens（arXiv 2605.23899）的 9 维评分药方 + SkillOpt（arXiv 2605.23904）的 validation-gated 验证机制 + human in the loop 三层守关。
>
> 借鉴 Karpathy autoresearch 的自主实验循环，对 skills 进行持续优化。
> 核心理念：**评估 → 改进 → 实测验证 → 人类确认 → 保留或回滚 → 生成成果卡片**
> 原版 GitHub: https://github.com/alchaincyf/darwin-skill ｜ 增强版: https://github.com/kkkariel888/darwin-skill-plus

---

## 设计哲学

autoresearch 的精髓：
1. **单一可编辑资产** — 每次只改一个 SKILL.md
2. **双重评估** — 结构评分（静态分析）+ 效果验证（跑测试看输出）
3. **棘轮机制** — 只保留改进，自动回滚退步
4. **独立评分** — 评分用子agent，避免「自己改自己评」的偏差
5. **人在回路** — 每个skill优化完后暂停，用户确认再继续

与纯结构审查的区别：不只看 SKILL.md 写得规不规范，更看改完后**实际跑出来的效果是否更好**。

---

## 评估 Rubric（9维度，总分100）

> **设计依据**：基于 SkillLens 论文（arXiv 2605.23899）实证发现——LLM-as-judge 评估 skill 质量准确率仅 46.4%（接近随机），加入 meta-skill 三维度后提升到 73.8%。本 rubric 强化 dim3 / dim5 评分标准，新增 dim9「反例与黑名单」，权重平衡到 100。**目的：让评分对真实质量更敏感，减少 LLM judge 的乐观偏差。**

### 结构维度（59分）— 静态分析

| # | 维度 | 权重 | 评分标准 |
|---|------|------|---------|
| 1 | **Frontmatter质量** | 7 | name规范、description包含做什么+何时用+触发词、≤1024字符、**禁结尾加"灵活应用/根据情况判断"等空话尾巴** |
| 2 | **工作流清晰度** | 12 | 步骤明确可执行、有序号、每步有明确输入/输出 |
| 3 | **失败模式编码** | 12 | **必须显式编码失败模式**（写出"如果 X 失败 → Y"的明确分支）；有fallback路径、错误恢复；**只写正向流程而不写失败分支扣 ≥3 分**（SkillLens meta-skill 维度） |
| 4 | **检查点设计** | 6 | 关键决策前有用户确认、防止自主失控；**检查点必须显性标记（🔴/STOP/CHECKPOINT），仅靠"如果...建议..."措辞不算** |
| 5 | **可执行具体性** | 18 | 不模糊、有具体参数/格式/示例、可直接执行；**禁止"建议/可以考虑/根据情况/灵活把握/视情况而定"等软化措辞**——出现 ≥3 处扣 ≥3 分（SkillLens actionable specificity 维度） |
| 6 | **资源整合度** | 4 | references/scripts/assets引用正确、路径可达 |

### 效果维度（35分）— 需要实测

| # | 维度 | 权重 | 评分标准 |
|---|------|------|---------|
| 7 | **整体架构** | 12 | 结构层次清晰、不冗余不遗漏、与花叔生态一致；**冗余/AI腔废话段落（说白了/换句话说/首先其次综上等花叔禁用词）出现一处扣 1 分** |
| 8 | **实测表现** | 23 | 用测试prompt跑一遍，输出质量是否符合skill宣称的能力 |

### Meta-skill 维度（6分）— 反例与黑名单

| # | 维度 | 权重 | 评分标准 |
|---|------|------|---------|
| 9 | **反例与黑名单** | 6 | **skill 必须有"不要做什么"的反例清单**；只写"应该做 X"没有"不要做 Y"扣 ≥3 分；红灯/危险动作/反模式应单独章节列出（SkillLens risk-action blacklist 维度） |

### 评分规则
- 维度1-7、9：每个维度打 1-10 分，乘以权重得到该维度得分
- 维度8（实测表现）：跑2-3个测试prompt，按输出质量打1-10分
- **总分 = Σ(维度分 × 权重) / 10**，满分100
- ⚠️ **绝对总分只用于 triage（粗排「哪支最弱、先改谁」），绝不用于 keep/revert**。实测：同一份**未改**文字换个 judge 评，总分可摆 **±8**（一支只加了 3 个 🔴 字元的 skill、单评却 −8.5，全是 judge 换尺、非真实退步）。keep/revert 一律走 **Phase 2 的 paired 比较**。
  - **为什么**：LLM judge 给的是**抽样、不是测量**——分数住在「文字 × 该 judge 当下选的标准」里，不是文字属性。绝对总分 = 用**两台未校准磅秤**量节食前后，差值大半是磅秤差；paired = **同一台磅秤**量前后，误差相减抵销。pairwise preference >> absolute scoring 是 LLM judge 的已知结论（RLHF 用 pairwise 不用绝对分同因）。

### Rubric 的实证基础

rubric 设计依据来自 **SkillLens 论文（arXiv 2605.23899）** + **本机 controlled study**：

- SkillLens 发现 LLM-as-judge 准确率仅 46.4%（接近随机），加入 meta-skill 三维度后升到 73.8%
- 本机对 huashu-research 做 4 类 degradation → 5 个独立 judge 盲测一致 V1>V2，Δ 均值 +46.5（5/5 high confidence）

**结论**：rubric 能识别 gross degradation，但 fine-grained quality difference 仍不可信，**重要决策必须人审**。

→ 详细论文证据 + 5 judges 完整数据 + HL 实战案例数字见 [references/skilllens-evidence.md](references/skilllens-evidence.md)

### 关于「实测表现」维度

这是与纯结构评分最大的区别。评分方式：

1. 为每个skill设计2-3个**典型用户prompt**（不是边缘case，是最常见的使用场景）
2. 用子agent执行：一个带skill跑，一个不带skill跑（baseline）
3. 对比输出质量，从以下角度打分：
   - 输出是否完成了用户意图？
   - 相比不带skill的baseline，质量提升明显吗？
   - 有没有skill引入的负面影响（过度冗余、跑偏、格式奇怪）？

若子 agent 不可用（超时/资源限制），退化为「干跑验证」：读完 skill 后模拟一个典型 prompt 的执行思路，判断流程是否合理；必须在 results.tsv 标注 `dry_run`。**dry_run 比例 > 30% → 评估失效警告**（来自本机 controlled study：dim8 实测维度权重 23%，无 full_test 验证时分数不可信）。

---

## Runtime 适配性审查（gate 项，独立于 9 维度评分）

skill 应当能在 Claude Code / Codex / Cursor / OpenClaw / Hermes / Gemini CLI / OpenCode 等 50+ skills-compatible runtime 通用——否则其他 agent 解析时会被「在 Claude Code 里」「Claude Code skill」等措辞误判为「不是给我用的」直接拒装（实例：nuwa-skill 因此被 Marvis agent 拒绝）。

### Phase 1 基线评估时强制跑一次红灯扫描

```bash
grep -nE "(在 Claude Code|Claude Code skill|Claude Code 用户|Cursor only|Codex 中|^\[!\[Claude Code|~/\.claude/skills/[a-z]|/plugin install\b)" SKILL.md README.md 2>/dev/null
```

输出非空 = 红灯命中，**但须先读命中行上下文排除假阳性**（grep 命令本身/反例引用/讲解该规则的元陈述=假阳性，记 `runtime_scan=false_positive` 不改；判别表见 references/runtime-neutrality.md）→ 确认是真红灯（指令性用法）才强制把 Phase 2 第一轮定为 P0「runtime drift 修复」（写入 results.tsv 的 note 列 `runtime_warn=N`）。

### 例外（允许的「Claude Code 痕迹」）

frontmatter 触发词、花叔生态内部 skill 名引用、明确标注 runtime-specific 章节、commit message——这些正当出现，不算红灯。

→ 红灯/绿灯完整对照表 + 例外清单详细规则 + Phase 1/2/3 各阶段审查时机见 [references/runtime-neutrality.md](references/runtime-neutrality.md)

---

## 平台适配体检（Plus 新增，gate 项，独立于 9 维度评分）

上面的 Runtime 审查只管**措辞**（别写死「在 Claude Code 里」）。这一节管**能不能真跑起来**：同一个 skill，在本机终端能跑，到 Cowork、Codex 的沙盒里常常卡死（下载被拦、没有 brew、没有显卡、碰不到桌面）。

**目标平台**：默认只管 2 个——`claude-desktop`（Claude 桌面 app 的 Code 页面）和 `codex`（OpenAI Codex，默认沙盒，联网要批准）。开发者没提别的就不管别的；提了就加：规范表 `assets/platforms.json` 里有的直接加（`claude-code` 终端、`cowork` 隔离环境），**没有的新 AI** 先上网找它的官方文档（插件/skill 装在哪、清单文件叫什么、怎么从 GitHub 装和自动更新），照规范表格式写进仓库根目录 `agent-platforms.json` 的 `custom`，找不到官方文档就老实告诉开发者、不要猜。仓库里已有 `agent-platforms.json` 的以它为准。写进 results.tsv 的 note：`platforms=...`。

1. **Phase 0.5 加环境模拟 prompt**：目标里每个沙盒平台（codex，以及开发者点名的 cowork 等）至少 1 个，开头写清环境，比如「（环境：Cowork，Linux 隔离环境，没有 brew、没有显卡，只能访问白名单网站，只能读写用户选的文件夹）」+ 一句正常用户请求。expected 写「不用环境里没有的东西；卡住时告诉用户具体放开哪个网址 / 换哪种做法，不是让用户在看不懂的选项里选」。
2. **Phase 1 跑静态体检**：`python3 <本skill>/scripts/platform_check.py <仓库根目录> [--platforms <目标平台>]`（不填就按 agent-platforms.json，没有就按默认），结果写进基线评分卡备注。
   - 有 ❌（装不上、只认 Mac 又没退路、依赖没自动装、下载源在该平台被拦）→ Phase 2 第一轮定为 **P0「平台适配修复」**，note 写 `platform_fail=N`。
   - 只有 ⚠️ → 当候选改进，和其他维度一起排优先级；改没改好由环境模拟 prompt 的 paired 比较说了算。
3. **改好，不只是查**（和 Phase 2 的 P0 一起做）：
   - 装不上 / README 没写这个 AI 怎么装 → `python3 <本skill>/scripts/platform_fix.py <仓库根目录> [--platforms ...] [--add 新AI]`：自动补安装文件和 README 装法，把目标记进 `agent-platforms.json`，`tools/bump.py` 换成能改齐所有 AI 版本号的新版。输出有 ❗ 的照那个 AI 官方文档手写。
   - 只认 Mac → 用 `shutil.which` / `platform.system` 判断，给别的系统的办法或写清只能在 Mac 做；第三方依赖 → 脚本开头 `pip install --target <缓存>` 自动装；下载源被拦 → 换 GitHub / PyPI，SKILL.md 出错表写清被拦时让用户放开哪几个网址；写桌面 → 退回用户给的文件夹；打开网页 → 「在哪打开」那节每个目标 AI 写一句。
4. **Phase 3.5 再跑一次**：不能有 ❌（最多修 3 次，还不行写进报告）。⚠️ 原样列进报告。能真跑的真跑一次：Code 页面就是本机，挑一个典型任务从头跑到尾；本机有 `codex` 命令就把仓库复制到临时文件夹，`codex exec -C <临时文件夹> "读 <SKILL.md 路径>，照着把第 0、1 步做完，报告卡在哪"`。
5. **CHECKPOINT 和报告里诚实写**：静态体检 + 环境模拟只能证明「写法对」。沙盒的网络白名单、真机交互，要在那个平台真跑一次才算数——报告里给一张「在哪能用」表（每个目标 AI 一行：✅ / ❌ 卡在哪 / 没实测），**不许写「全平台可用」**。

| 情况 | 怎么办 |
|---|---|
| 修 ❌ 要换下载源 / 换依赖 | 优先用该平台能访问的源（GitHub、PyPI 一般能通；huggingface 在 Cowork 实测被拦），改完在本机实测一次脚本还能跑 |
| skill 本来就只给一个平台用（名字或 README 写明） | `--platforms` 只填那一个，其他平台不查 |
| 体检脚本自己报错 | 把输出原文告诉用户，跳过本节，报告里写「平台体检没跑成」 |

---

## 真实体验关（Plus 新增，复杂项目必过，gate 项）

9 维度评分只看说明书写得对不对，测不出「慢、点了没反应、图看不全、文件夹一堆垃圾」。**会开网页、要确认两次以上、用一次超过 3 分钟、会往用户文件夹写文件——满足一条就必须过这一关**，否则不进发布。完整做法见 [references/experience-gate.md](references/experience-gate.md)，要点：

1. **Phase 0.6 写体验剧本**：被测仓库 `tests/ux/journey.json`（用户是谁、输入什么、每一步看到什么点什么等多久、最后拿到什么）+ 体验标准（默认：10 秒内有反馈、干等不超过 30 秒、页面点了 5 秒内有反应、用户最多发 3 条消息、结果一次看完、文件夹只留用户要的）+ 一份很小的测试材料 `tests/ux/fixture/`。**🔴 CHECKPOINT**：用大白话给开发者看剧本，点头再往下。新项目开发前就写，第一版就照着做。
2. **Phase 1 真跑摸底一次**：派执行者把 skill 真做一遍，用 `scripts/ux_log.py` 记流水；要打开的页面由 `scripts/ux_page.py` 像真人一样点（不花 token）；`scripts/ux_report.py` 出体验成绩单；再派最便宜的模型当「小白评审」只看截图挑毛病。
3. 成绩单有 ❌ → Phase 2 第一轮 **P0「体验修复」**（改 skill，不改剧本放水）。
4. **Phase 3.5 真跑验收一次**：不能有 ❌，也不能比上次慢、多点、多问；变差就撤回。
5. **省钱**：能用脚本的不用 AI，测试材料要小，假用户的回答和点击写死，只真跑两次，只重跑改过的那段，超时就停。
6. 报告里放成绩单（每一步多少秒、用户点几下、发几条消息），写清在哪个 AI 里真跑的。

## 自动发布准备：体检 + 自动补齐（Plus 新增，独立于 9 维度评分）

skill 写得再好，用户收不到新版也白改。被优化的 skill 在 git 仓库里时，达尔文增强版**优化完自己把发布准备做完，不只是提醒**。只有推送到 GitHub 前停一次（公开操作，推出去收不回）。

**Phase 1（体检，只看不改）**：`python3 <本skill>/scripts/autoupdate_check.py <仓库根目录> --base <优化前 commit> [--prefix ariel-]`（作者要求 skill 统一前缀、打 `/前缀` 能调出来时加 `--prefix`；P8 ❌ 就把 skill 文件夹和 name 改成前缀开头，插件名不改），结果写进基线评分卡的备注。

**Phase 3.5（自动补齐，所有 skill 优化完、汇总报告前，不用再问用户）**：
1. 在优化分支上跑 `python3 <本skill>/scripts/autoupdate_fix.py <仓库根目录> --base <优化前 commit>`。它自动：补 `tools/bump.py`（写死插件名的换成通用版）、`tools/check_version_bump.py` + `.github/workflows/version-check.yml`、`.gitignore`、skill 的 `scripts/update_check.py`，并且**版本号改齐、改了内容就最后一位 +1**。
2. 最后一行是 `FIX=NEED_LAYOUT`（不是插件市场结构）→ 照 [references/auto-update-layout.md](references/auto-update-layout.md) 搭好结构：`git mv` 把 SKILL.md 和它的文件夹挪到 `plugins/<名>/skills/<名>/`，写齐 4 个 json（版本号 1.0.0），再跑一次第 1 条。
3. 脚本说加了或换了 `update_check.py` → 在那个 SKILL.md 开工第一步写（已有旧写法就换掉）：「`python3 <本skill>/scripts/update_check.py`：开工查新版本（几秒）。最后一行是 `STATUS=live` → 跟用户说一句「用上了新版 X」，然后读它打印的 `LIVE_SKILL_DIR` 文件夹里的 `SKILL.md`，**这次就按新版做**（从新版第 0 步的下一条接着做，之后 `<本skill>` 都指那个文件夹）；是 `updated` 或 `outdated` 就说一句；其他情况不吭声。」
4. README 照 [references/readme-install.md](references/readme-install.md) 补缺的安装说明（插件市场装法、命令行装法下面「打开自动更新」那一句、手动复制不会自动更新的提醒），只加不删。
5. 再跑体检，**不能有 ❌**；有就按提示修，最多 3 次，还不行写进报告。
6. `git add -A && git commit -m "release: 自动更新补齐 + 版本号 <旧> → <新>"`。

**Phase 3 的 🔴 CHECKPOINT** 一起给用户看：优化改了什么 + 发布准备补了什么 + 版本号从几到几 + 体检结果。按钮：**推送并开合并申请（推荐）** / **先不推**。用户同意后 `git push -u origin <分支>` → `gh pr create`；仓库还没上 GitHub 就问仓库名和公开/私有，`gh repo create <用户名>/<名> --source . --remote origin --push`。合并后读 `https://raw.githubusercontent.com/<用户名>/<仓库>/HEAD/plugins/<名>/.claude-plugin/plugin.json`，版本号对上才告诉用户「已发出去」。

| 情况 | 怎么办 |
|---|---|
| skill 不在 git 仓库（比如直接放在 skills 文件夹） | 跳过本节，报告写「不在 git 仓库，用户收不到更新；要开源就先建仓库」。 |
| 仓库是别人的（push 被拒） | 不推送，告诉用户要先 fork。 |
| 体检发现密钥 / 个人路径 | 个人路径直接改成 `~` 或相对路径；密钥**不替用户处理**，停下告诉用户去作废。 |
| 脚本输出 `FIX=ERROR` | 把输出原文告诉用户，跳过本节其余步骤。 |

## 自主优化循环

### Phase 0: 初始化

0. `python3 <本skill>/scripts/update_check.py`：查达尔文增强版自己有没有新版本。最后一行是 `STATUS=live` → 跟用户说一句「用上了新版 X」，然后读它打印的 `LIVE_SKILL_DIR` 文件夹里的 `SKILL.md`，**这次就按新版做**（从新版第 0 步的下一条接着做，之后 `<本skill>` 都指那个文件夹）；是 `updated` 或 `outdated` 就说一句；其他情况不吭声。记下每个被优化 skill 所在仓库优化前的 commit（自动发布准备的 `--base` 用）。

```
1. 确认优化范围：
   - 全部skills → 扫描 .claude/skills/*/SKILL.md
   - 指定skills → 用户指定列表
2. 创建 git 分支：auto-optimize/YYYYMMDD-HHMM
3. 初始化 results.tsv（如不存在）
4. 读取现有 results.tsv 了解历史优化记录
```

### Phase 0.5: 测试Prompt设计

在评估之前，为每个skill设计测试prompt。这步很关键——没有测试prompt，「实测表现」维度就打不了分。

```
for each skill:
  1. 读取 SKILL.md，理解它做什么
  2. 设计2-3个测试prompt，覆盖：
     - 最典型的使用场景（happy path）
     - 一个稍复杂或有歧义的场景
  3. 保存到 skill目录/test-prompts.json：
     [
       {"id": 1, "prompt": "用户会说的话", "expected": "期望输出的简短描述"},
       {"id": 2, "prompt": "...", "expected": "..."}
     ]
```

展示所有测试prompt给用户，**确认后再进入评估**。测试prompt的质量决定了优化方向是否正确。

### Phase 0.6: 体验剧本（复杂项目必做，Plus 新增）

复杂项目（会开网页 / 要确认两次以上 / 用一次超过 3 分钟 / 会往用户文件夹写文件）照 [references/experience-gate.md](references/experience-gate.md) 写 `tests/ux/journey.json`、`tests/ux/page.json` 和很小的测试材料 `tests/ux/fixture/`，和测试 prompt 一起给用户看。**🔴 CHECKPOINT**：剧本用大白话讲（每一步用户看到什么、点什么、最多等多久），用户点头再进 Phase 1。Phase 1 基线时真跑一次出体验成绩单。

### Phase 1: 基线评估（Baseline）— triage 用途

> **本阶段绝对分数是 triage 排名（决定先改谁），不是 keep/revert 基准**。judge 对 gross 差异会一致（「哪支最弱」可信），对 fine-grained delta 不可信（±8 噪音）。keep/revert 在 Phase 2 用 paired 比较。

```
for each skill in 优化范围:

  # 结构评分（主agent可以做）
  1. 读取 SKILL.md 全文
  2. 按维度1-7逐项打分（附简短理由）

  # 效果评分（用子agent做，独立于主agent）
  3. 对每个测试prompt，spawn子agent：
     - with_skill: 带着SKILL.md执行测试prompt
     - baseline: 不带skill执行同一prompt
  4. 对比两组输出，打维度8的分

  # 汇总
  5. 计算加权总分
  6. 记录到 results.tsv

  # Plus：两项体检（只看不改，结果写进评分卡备注）
  7. autoupdate_check.py（用户能不能自动更新）
  8. platform_check.py（各目标平台能不能装、能不能跑），有 ❌ 就把 Phase 2 第一轮定为 P0
```

**如果子agent不可用**（超时、环境限制），维度8用干跑验证打分，标注 `dry_run`。不要因为跑不了测试就跳过这个维度——哪怕是模拟推演也比完全不看效果好。

基线评估完成后，展示评分卡：

```
┌──────────────────────────┬───────┬──────────────┬──────────────┐
│ Skill                    │ Score │ 结构短板      │ 效果短板      │
├──────────────────────────┼───────┼──────────────┼──────────────┤
│ huashu-proofreading      │ 78    │ 边界条件      │ 测试prompt2  │
│ huashu-slides            │ 72    │ 指令具体性    │ baseline持平  │
├──────────────────────────┼───────┼──────────────┼──────────────┤
│ 平均                     │ 75    │              │              │
└──────────────────────────┴───────┴──────────────┴──────────────┘
```

**🔴 CHECKPOINT · 🛑 STOP：暂停等用户确认，再进入优化循环。**

### Phase 2: 优化循环

用户确认后，按基线分数从低到高排序，先优化最弱的。

```
for each skill:
  round = 0
  while round < MAX_ROUNDS (默认3):
    round += 1

    # Step 1: 诊断
    找出加权短板最大的维度：weighted_gap = weight × (10 - score) / 10，结构或效果都算
    # /10 与「总分 = Σ(维度分 × 权重) / 10」同标度：weighted_gap 就是该维度还能贡献的总分数
    # 为什么不用「原始分最低」：低权重维度会制造进步幻觉——issue #18 实战中
    # dim9（权重6，gap 5.3）原始分最低被优先修，而 dim8（权重23）加权短板最大（11.5）却 4 轮未动
    # 加权短板相近（差距 ≤ 1.0，同上述标度）时，回退为原始分升序
    # HL-3 警告：dim2/dim3/dim4 是相关簇，修一个时另两个常跟着涨
    # → 不要因为 dim3 短板最大就单独修，要看整簇短板再决定是否同步改

    # Step 2: 提出改进方案
    针对该维度，生成1个具体改进方案：
      - 改什么（具体段落/行）
      - 为什么改（对应rubric哪条）
      - 预期提升多少分

    # Step 3: 执行改进
    编辑 SKILL.md
    git add + commit（message: "optimize {skill}: {改进摘要}"）

    # Step 4: Paired 重新评估（取代绝对重打分——绝对分数 judge 噪音 ±8、淹没保守编辑的 +3~8 真实增益）
    spawn N=3 独立 judge，每个【同一次 call 内】读两版：
      - 改前版：git show HEAD:<skill-path>/SKILL.md（上一个 kept commit）
      - 改后版：working tree 当前 SKILL.md
    照 9 维 rubric 当【比较准则】（不是各打绝对分），回 {better | worse | tie} + margin{clear|slight} + 一句理由。
    关键：同一 judge 在一次 call 内比两版 → 它那把不准的尺对两版【等量作用、在比较时抵销】(within-judge cancellation)，
    这正是 paired 优于绝对的机制。N 取奇数（默认 3；close call 升 5）。

    # Step 5: 共识决策（多数决，取代「新总分 > 旧总分」）
    cur = 投 better 的 judge 数；wor = 投 worse 的；
    if cur >= wor:  # 多数说改后 ≥ 改前（含 tie）
      status = "keep"
      # HL-4 见好就收：连续 2 轮多数 judge 判 margin=slight 或 tie → break 进 Phase 3
    else:           # 多数说 worse —— 这才是真退步（已扣掉换尺噪音）
      status = "revert"
      git revert HEAD（创建新commit回滚，不用 reset --hard）
      记录到 results.tsv（note 记 vote 比数 + 一句 worse 理由）
      break
    # 单评绝对分数出现「负 delta」≠ revert 信号；必须经 paired 多数判 worse 才 revert（否则在丢真实增益）

    # Step 6: 日志
    results.tsv 追加行

  # === 🔴 CHECKPOINT · 每个 skill 优化完后强制人审 ===
  展示该skill的改动摘要：
    - git diff（改前 vs 改后）
    - 分数变化（哪些维度提升/下降）
    - 测试prompt输出对比（如果跑过的话）
  等用户确认 OK 再继续下一个skill。
  如果用户说"不好"，回滚到该skill的优化前版本。
```

### Phase 2.5: 探索性重写（按需触发）

当 hill-climbing 连续2个skill都在 round 1 就 break（涨不动）时，提议一次「探索性重写」：

```
1. 选一个瓶颈skill
2. git stash 保存当前最优版本
3. 从头重写SKILL.md（不是微调，是重新组织结构和表达方式）
4. 重新评估
5. if 重写版 > stash版: 采用重写版
   else: git stash pop 恢复
```

这解决了 hill-climbing 的局部最优问题——有时候需要「先拆后建」才能突破瓶颈。
**🔴 CHECKPOINT · 🛑 STOP：必须征得用户同意后才执行。**

### Phase 3: 汇总报告

```
## 优化报告

### 总览
- 优化skills数：N
- 总实验次数：M
- 保留改进：X（Y%）
- 回滚次数：Z
- 实测验证：A次完整测试 / B次干跑

### 分数变化
┌──────────────────────────┬────────┬────────┬────────┐
│ Skill                    │ Before │ After  │ Δ      │
├──────────────────────────┼────────┼────────┼────────┤
│ huashu-proofreading      │ 78     │ 87     │ +9     │
│ huashu-slides            │ 72     │ 83     │ +11    │
├──────────────────────────┼────────┼────────┼────────┤
│ 平均                     │ 75     │ 85     │ +10    │
└──────────────────────────┴────────┴────────┴────────┘

### 主要改进
1. [skill-A] 补充了边界条件处理，测试输出质量提升明显
2. [skill-B] 重组了workflow结构，baseline对比优势增大

### 自动发布准备（Plus）
- [skill-A] 仓库 xxx：已补 GitHub 自动检查、通用 bump.py、README 自动更新说明；版本号 1.1.2 → 1.1.3；体检 ✅ 全部通过
- [skill-B] 不在 git 仓库：用户收不到更新，要开源先建仓库

### 真实体验（Plus）
体验成绩单：总耗时、每一步多少秒（对比标准和上次）、用户点了几下 / 发了几条消息、❌ 项和怎么修的、小白评审的意见、在哪个 AI 里真跑的。简单 skill 写「跳过体验关」。

### 平台适配（Plus）
| 平台 | 体检 | 环境模拟测试 | 真机验证 |
|---|---|---|---|
| Claude Code 终端 | ✅ | — | ✅ 本机跑过 |
| Cowork | ✅（修了 2 处） | 3-0 胜 | ⏳ 还没在 Cowork 真跑 |
```

---

## results.tsv 格式

```tsv
timestamp	commit	skill	old_score	new_score	status	dimension	note	eval_mode
2026-03-31T10:00	baseline	huashu-proofreading	-	78	baseline	-	初始评估	full_test
2026-03-31T10:05	a1b2c3d	huashu-proofreading	78	84	keep	边界条件	补充fallback	full_test
2026-03-31T10:10	b2c3d4e	huashu-proofreading	84	82	revert	指令具体性	过度细化	dry_run
```

`eval_mode` 列：`paired`（同 judge 比改前/改后，**keep/revert 权威依据**）｜`full_test`（子agent 跑 prompt）｜`dry_run`（模拟推演、仅供参考）。
paired 行：`new_score` 栏记 vote 比数（如 `3-0 better`），`note` 记一句裁断理由。例：
```tsv
2026-06-10T06:30	paired	some-skill	（绝对 87.3→78.8 = judge 噪音）	3-0 better	paired 推翻单评假退步	paired
```
文件位置：`~/.darwin-skill-plus/results.tsv`（放在插件目录外，插件自动更新时不会被覆盖；目录不存在就先建）

---

## 实战 high-leverage 操作（精髓速查）

4 条经实战验证（huashu-gpt-image +10.85 / huashu-weread-advisor +14.9 / claude-design +16.5）。详细案例数据见 [references/skilllens-evidence.md](references/skilllens-evidence.md) 的「HL 实战案例」节。

- **HL-1（dim4）显性视觉标记是杠杆**：加 🔴 CHECKPOINT / 🛑 STOP，靠「必须」措辞不行——LLM 解析时扫描视觉标记。4 行改动撬动 dim4 +3 分
- **HL-2（dim3）if-then 三段式 fallback 表**：把「症状/解法」两列升级为「触发条件 / 一线修复 / 仍失败兜底」三段式。SkillLens failure-mechanism encoding 维度的落地
- **HL-3（Phase 2 诊断）维度相关簇警告**：dim2/3/4 是相关簇——修 dim3 时 dim2 常跟着涨。「找最大加权短板维度」时同时看相关簇短板再决定是否同步改
- **HL-4（Phase 2 退出）触顶自动 break**：连续 2 轮 Δ < 2 分 → break 进 Phase 3。+0.15 是停手信号不是继续信号；硬凑 MAX_ROUNDS=3 引入 over-engineering

---

## 优化策略库

按优先级排序，每轮只做最高优先级的一个：

### P0: Runtime 适配性问题（gate 项命中 → 必须先修）
- README/SKILL.md 出现红灯措辞（如「在 Claude Code 里」「Claude Code skill」）→ 替换为 runtime-neutral 措辞
- Badge 钉死单一 runtime → 改为 `Agent Skills Standard` + `skills.sh` + `Multi-Runtime` 三个中立 badge
- 安装章节只给一种 runtime 的路径 → 改为「一行命令（auto-detect）+ 手动路径表 + 作为参考资料」三层结构
- 工作流硬编码 runtime-specific 工具且无 fallback → 给出通用替代方案或标注「仅在某 runtime 可用」
- 例外：skill 名明确标注单 runtime（如 `xxx-codex`）的，可跳过本项

### P0: 效果问题（实测发现的）
- 测试输出偏离用户意图 → 检查skill是否有误导性指令
- 带skill比不带还差 → skill可能过度约束，考虑精简
- 输出格式不符合预期 → 补充明确的输出模板

### P1: 结构性问题
- Frontmatter缺少触发词 → 补充中英文触发词
- 缺少Phase/Step结构 → 重组为线性流程
- 缺少用户确认检查点 → 在关键决策处插入

### P2: 具体性问题
- 步骤模糊（"处理图片"）→ 改为具体操作和参数
- 缺少输入/输出规格 → 补充格式、路径、示例
- 缺少异常处理 → 补充 "如果X失败，则Y"

### P3: 可读性问题
- 段落过长 → 拆分+用表格
- 重复描述 → 合并去重
- 缺少速查 → 添加TL;DR或决策树

---

## 异常与边界条件

流程假设环境理想，但实操常遇异常。以下预定义 fallback，保证优化过程不会「一跑就卡住」。

| 场景 | 触发条件 | 处理动作 |
|---|---|---|
| 不在 git 仓库 | `git rev-parse` 失败 | 询问用户：执行 `git init` 或回退到文件备份；用户选后者则 `cp SKILL.md SKILL.md.bak.YYYYMMDD-HHMM` 代替 revert |
| results.tsv 缺失 | 文件不存在 | 新建并写表头行（9列：含 eval_mode） |
| results.tsv 损坏 | 列数不匹配 / 非TSV | 备份为 `.bak.YYYYMMDD-HHMM` 后重建，告知用户 |
| 分支已存在 | `git checkout -b` 失败 | 分支名末尾加 `-2` / `-3`；第3次失败则切回现有分支并询问继续还是新起 |
| `git revert` 失败 | 冲突 / 工作树脏 | 先 `git stash`，重试；仍失败则从上一个 commit 的 SKILL.md 读出覆盖当前文件手动恢复 |
| MAX_ROUNDS 触顶（默认3） | 已跑3轮仍有短板 | 不强制 break，展示当前最弱维度问用户「继续加1轮 / 进入Phase 2.5 / 收工」 |
| 优化后超 150% 体积 | 新文件 > 原 × 1.5 | 拒绝提交，回到改进步骤精简（删冗余/合并重复），再评 |
| test-prompts.json 已存在 | 文件已在 skill 目录 | 默认复用并展示，问用户「复用 / 重写 / 追加」三选一 |
| SKILL.md 找不到 | 目录存在但无 SKILL.md | 该 skill 终止，results.tsv 记 `status=error`，继续下一个 |
| 分数计算规则 | 浮点精度漂移 | 总分保留 1 位小数，改进需严格 > 旧分（不靠四舍五入） |

**原则**：异常先告知用户，再按规则处理；绝不静默跳过或静默失败。

---

## darwin 操作反例黑名单（dim9 应用：darwin 自己优化时不要做的事）

来自本机 results.tsv 早期 40 次 0 revert 的教训 + Judge G/H 自指评估暴露的反模式。每条都是**真实踩过的坑**。

| # | 反模式 | 为什么不要做 | 替代做法 |
|---|---|---|---|
| 1 | **同 context 自评自改** | 改完后立刻在同一 Claude session 打分，会有「我刚改的肯定更好」乐观偏差（SkillLens 实证 LLM-as-judge 准确率仅 46.4%）| 必须 spawn **独立子 agent**；keep/revert 走 **paired 比较**（同 judge 一次读改前+改后）的**奇数 N 多数决**，**不用绝对分数 delta**（绝对分跨 judge ±8 噪音、不可比） |
| 1b | **拿绝对分数 delta 当 keep/revert 棘轮** | 绝对总分是抽样不是测量；baseline judge 与 rescore judge 用不同「标准尺」，差值大半是换尺、非真实质量变化（实测一支纯加标记的 skill 单评 −8.5、全是换尺）| 绝对分只做 triage 排名；keep/revert 用 paired 多数决，within-judge cancellation 消除换尺污染 |
| 2 | **`git reset --hard` 当回滚** | 会丢工作树未提交改动；CI 历史断裂 | 用 `git revert HEAD` 创建反向 commit，保留可追溯链 |
| 3 | **为凑分增冗余** | 触顶后继续硬改往往是「加废话/加段落让 LLM 觉得更详细」，实际质量不变 | 触顶信号（连续 2 轮 Δ<2 分）→ break 进 Phase 3，**见好就收** |
| 4 | **跳过 test-prompts 直接评分** | 没有 test-prompts 的 dim8 是凭空打分，权重 23% 等于编造 | Phase 0.5 强制设计 2-3 prompts；若用户不给，默认编 3 个并展示确认 |
| 5 | **轮内改多个维度** | 多变量同时变，分数升降无法归因到具体改动 | 每轮 1 个维度；相关簇（dim2/3/4）改其一时观察另两个是否跟涨 |
| 6 | **dry_run 比例 > 30%** | dim8 实测维度形同虚设，分数虚高（早期 40 次记录 67% dry_run，0 revert） | 强制至少 1 个真实 full_test；dry_run 多的优化在 results.tsv 显式打 ⚠️ |
| 7 | **静默跳过异常** | 遇到 git/tsv 异常时静默继续，破坏 ratchet 完整性 | 异常表 10 条 fallback 必须先告知用户再处理 |
| 8 | **忽视维度相关性单独优化** | dim2/3/4 是相关簇，单独优化 dim2 时常发现已被前轮 dim3 修复推到顶 | 找最大加权短板维度时同时看相关簇短板，决定是否同步改 |

| 11 | **复杂项目只看说明书打分、不真跑一遍**（Plus 新增） | 测不出慢、点了没反应、图看不全、文件夹一堆垃圾；用户实操一遍全是坑（实例：B-roll 选风格十几分钟、页面点了 AI 不动） | 走真实体验关：写剧本、真跑、按成绩单修 |
| 9 | **优化完不涨版本号 / 只提醒不补齐**（Plus 新增） | 内容改了、版本号没变，插件市场认为没有新版，用户永远收不到这次优化 | Phase 3.5 自动跑 `autoupdate_fix.py`，补齐并涨版本号后再进 CHECKPOINT |
| 10 | **只在本机测过就说「全平台能用」**（Plus 新增） | 本机能上网、有 brew、有显卡、能写桌面；Cowork / Codex 沙盒一样都没有，用户一跑就卡（实例：听写模型放 huggingface，Cowork 下载被拦） | 跑 `platform_check.py` + 环境模拟 prompt；报告里把没真机验证的平台列出来 |

**触发场景**：每轮 Phase 2 改动前对照本表一次。任一反模式命中 → 改方案重写。

---

## 约束规则

1. **不改变skill的核心功能和用途** — 只优化"怎么写"和"怎么执行"，不改"做什么"
2. **不引入新依赖** — 不添加skill原本没有的scripts或references文件
3. **每轮只改一个维度** — 避免多个变更导致无法归因
4. **保持文件大小合理** — 优化后SKILL.md不应超过原始大小的150%
5. **尊重花叔风格** — 中文为主、简洁为上
6. **可回滚** — 所有改动在git分支上，用git revert而非reset --hard
7. **评分独立性** — 效果维度必须用子agent或至少干跑验证，不能在同一上下文里「改完直接评」
8. **Runtime 中立性** — skill 必须能在 Claude Code、Codex、Cursor、OpenClaw、Hermes 等任何 skills-compatible runtime 中正常运行。除非 skill 名明确绑定单一 runtime（如 `xxx-codex`、`huashu-slides-codex`），任何「在 Claude Code 里」「Claude Code skill」「单一 badge 钉死」「安装命令只给 `.claude/skills/` 一种路径」都视为 gate 不通过，须在 P0 优先修复（详见「Runtime 适配性审查」章节）

---

## 使用方式

### 全量优化（推荐首次使用）
```
用户："优化所有skills"
→ Phase 0-3 完整流程
→ 默认：先基线评估，按分数升序优先优化最低 5-10 个
```

### 单个优化
```
用户："优化 huashu-slides 这个skill"
→ 只对指定skill执行 Phase 0.5-2
```

### 仅评估不改
```
用户："评估所有skills的质量"
→ 只执行 Phase 0.5-1（设计测试prompt + 基线评估），不进入优化循环
```

### 查看历史
```
用户："看看skill优化历史"
→ 读取并展示 results.tsv
```

---

## 设计灵感

> "You write the goals and constraints in program.md; let an agent generate and test code deltas indefinitely; keep only what measurably improves the objective."
> — Karpathy, autoresearch

本skill的对应关系：
- **program.md** → 本文件（评估rubric和约束规则）
- **train.py** → 每个SKILL.md
- **val_bpb** → ⚠️ **此处是 1.0 的概念错误源**：autoresearch 的 `val_bpb` 是**确定性 loss**（重跑同数），darwin 套到 **LLM-judge 分数（随机抽样）** 上却沿用「绝对值比大小」棘轮 → 不可重复的数当可重复用。修正：9 维 rubric 当 **paired 比较准则**、不当绝对 metric
- **git ratchet** → 保留 paired 多数判「改后 ≥ 改前」的 commit（不是「绝对总分更高」的 commit）
- **test set** → 每个skill的test-prompts.json

区别：增加了人在回路（autoresearch是全自主的，skill优化需要人的判断力），以及双重评估机制（结构+效果），因为skill的「好坏」比loss数值更微妙。

### 学术依据 & Credits

- **SkillLens**（arXiv [2605.23899](https://arxiv.org/abs/2605.23899)）：9 维 rubric 的实证来源（LLM 自评 46.4% → 加 meta-skill 三维度后 73.8%）。
- **SkillOpt**（arXiv [2605.23904](https://arxiv.org/abs/2605.23904)）：validation-gated edits 形式化框架。代码 [github.com/microsoft/SkillOpt](https://github.com/microsoft/SkillOpt)（`pip install skillopt`）、项目页 [microsoft.github.io/SkillOpt](https://microsoft.github.io/SkillOpt/)。🤝 2026-06-03 微软官方仓库已把 darwin-skill 列入集成名单。
- **autoresearch**：[github.com/karpathy/autoresearch](https://github.com/karpathy/autoresearch)，本 skill 1.0 的原始灵感。

---

## 成果卡片生成（Result Card）

每个skill优化完成后（或全量汇总后），自动生成视觉成果卡片，截图保存为PNG。

### 卡片模板

模板位置：`templates/result-card.html`

3种风格，每次随机选择一种：

| 风格 | CSS类 | URL hash | 视觉特点 |
|------|--------|----------|---------|
| Warm Swiss | `.theme-swiss` | `#swiss` | 暖白底+赤陶橙，Inter字体，干净网格 |
| Dark Terminal | `.theme-terminal` | `#terminal` | 近黑底+荧光绿，等宽字体，扫描线 |
| Newspaper | `.theme-newspaper` | `#newspaper` | 暖白纸+深红，衬线字体，双栏编辑风 |

### 生成流程

```
1. 复制 templates/result-card.html 到临时工作文件
2. 用 sed/编辑工具 替换占位数据：
   - data-field="skill-name" → 实际skill名
   - data-field="score-before/after/delta" → 实际分数
   - 9个维度的 dim-bar-before/after width → 实际百分比（若模板仍是旧 8 维布局，加一行 dim9 反例黑名单条目）
   - data-field="improvement-1/2/3" → 实际改进摘要
   - data-field="date" → 当前日期
3. 随机选择风格：hash 设为 swiss/terminal/newspaper 之一
4. 用 scripts/screenshot.mjs 截图（2x 高清，只截 .card 元素，自动 open 图片）：
   node <本skill>/scripts/screenshot.mjs \
     /abs/path/to/card.html /abs/path/to/output.png
   # 回退方案（脚本失败时）：
   npx playwright screenshot "file:///path/to/card.html#[theme]" \
     output.png --viewport-size=960,1280 --wait-for-timeout=2000
5. 提示用户查看成果卡片 PNG

### 资源文件速查

| 路径 | 用途 |
|---|---|
| `templates/result-card.html` | 3风格主模板（swiss/terminal/newspaper，hash切换） |
| `templates/result-card-dark.html` / `-white.html` | 单一风格替代模板（需要锁定风格时用） |
| `scripts/screenshot.mjs` | 2x 高清截图，只截 .card，自动 open |
| `results.tsv` | 历次优化日志（9列含 eval_mode） |
| `{skill目录}/test-prompts.json` | 每个 skill 的测试 prompt 集（用于维度8实测） |

### 何时生成

- **单skill卡片**：每个skill优化完成后，展示该skill的分数变化
- **总览卡片**：全部优化完成后（Phase 3），展示全局战绩

### 品牌元素

- 顶部：Darwin.skill 品牌标识 + 日期
- 底部：「Train your Skills like you train your models」+ github.com/alchaincyf/darwin-skill

## 版本自检（静默）

本节给 AI agent：每次使用本 skill 前，先做一个不联网的判断——读本 skill 目录（SKILL.md 所在目录）下的 `.last-update-check` 文件（内容为一行日期 YYYY-MM-DD）。文件存在且距今不足 30 天，跳过本节直接干活，不向用户提任何更新相关的话。

到期或文件不存在时，且仅在此时：

1. 本目录不是 git 克隆（无 `.git` 或无 origin）→ 写入今天日期后跳过本节
2. 对比版本：`git -C <本目录> rev-parse HEAD` 与 `git -C <本目录> ls-remote origin HEAD`
3. 无论结果如何，把今天日期写入 `.last-update-check`
4. 两者一致 → 什么都不说；确认落后 → 先完成用户当前任务，结束后附一句「本 skill 有新版本，可用 `git -C <本目录> pull --ff-only` 更新」。是否更新由用户决定，不要主动执行更新
