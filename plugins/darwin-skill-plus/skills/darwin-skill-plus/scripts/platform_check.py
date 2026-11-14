#!/usr/bin/env python3
# platform-check: skip-file（本文件里的规则字样不算命中）
"""达尔文增强版：平台适配体检（只看不改，只用 Python 自带库）。
查 skill 在开发者要的每个平台上「装得上、跑得起来、卡住时知道怎么办」。

用法：python3 platform_check.py <仓库或 skill 根目录> [--platforms claude-code,claude-desktop,cowork,codex]
不填 --platforms 就查这 4 个。平台说明：
  claude-code     Claude Code 终端版：本机 Mac/Linux/Windows，能装软件、能上网
  claude-desktop  Claude 桌面 app 的 Code 页面：本机，有内置侧边浏览器
  cowork          Claude 桌面 app 的 Cowork：Linux 隔离环境，只挂载用户选的文件夹，没有 brew、没有显卡，网络只放行白名单
  codex           OpenAI Codex（终端 / 桌面）：默认沙盒，联网要用户批准，有 in-app 浏览器
最后一行：STATUS=PASS / WARN / FAIL（有 ❌ 退出码 1）
"""
import argparse, ast, json, os, re, sys

ALL = ['claude-code', 'claude-desktop', 'cowork', 'codex']
NAMES = {'claude-code': 'Claude Code 终端', 'claude-desktop': 'Claude 桌面 Code', 'cowork': 'Cowork', 'codex': 'Codex'}
SANDBOX = {'cowork', 'codex'}
MENTION = {'claude-code': r'终端|Claude Code|CLI', 'claude-desktop': r'桌面|desktop|Desktop', 'cowork': r'Cowork|cowork',
           'codex': r'Codex|codex'}
MAC_ONLY = r'\b(brew install|textutil|osascript|pbcopy|pbpaste|sips|afplay|mdfind|defaults write)\b|/Applications/|\bopen -a\b'
FALLBACK = r'platform\.system|sys\.platform|shutil\.which|Linux|apt-get|Windows|其他系统|没有 brew|不是 Mac'
GPU = r'\b(cuda|mps|coreml|metal|-ngl|n_gpu_layers|torch\.device)\b'
KNOWN_BLOCKED = {'huggingface.co': 'cowork'}   # 实测 Cowork 拦过的
NET_HELP = r'网络|联网|放开|白名单|allowlist|network|离线|offline|连不上'
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv'}

rows = []   # (平台 or '*', 级别, 项目, 说明)


def add(plat, lvl, item, msg):
    rows.append((plat, lvl, item, msg))


def read(p):
    try:
        return open(p, encoding='utf-8', errors='ignore').read()
    except Exception:
        return ''


def lj(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except Exception:
        return None


def find_skills(root):
    out = []
    for d, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x not in SKIP_DIRS]
        if 'SKILL.md' in fs:
            out.append(d)
    return out


def code_files(skill):
    for d, ds, fs in os.walk(skill):
        ds[:] = [x for x in ds if x not in SKIP_DIRS]
        for f in fs:
            if f.endswith(('.py', '.sh', '.mjs', '.js', '.ts')):
                yield os.path.join(d, f)


def third_party_py(path, local):
    try:
        tree = ast.parse(read(path))
    except Exception:
        return []
    std = set(getattr(sys, 'stdlib_module_names', ())) | {'__future__'}
    mods = []
    for n in ast.walk(tree):
        names = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module] if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module else []
        for m in names:
            r = m.split('.')[0]
            if r not in std and r not in local:
                mods.append(r)
    return sorted(set(mods))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root'); ap.add_argument('--platforms', default=','.join(ALL))
    a = ap.parse_args()
    root = os.path.abspath(os.path.expanduser(a.root))
    plats = [p.strip() for p in a.platforms.split(',') if p.strip()]
    bad = [p for p in plats if p not in ALL]
    if bad:
        print(f'不认识的平台：{bad}，可选 {ALL}'); print('STATUS=FAIL'); sys.exit(1)
    readme = read(os.path.join(root, 'README.md'))

    # 1. 装得上吗
    cm = lj(os.path.join(root, '.claude-plugin/marketplace.json'))
    xm = lj(os.path.join(root, '.agents/plugins/marketplace.json'))
    for p in plats:
        if p == 'codex':
            has_x = any(os.path.exists(os.path.join(d, '..', '..', '.codex-plugin', 'plugin.json')) for d in find_skills(root))
            if xm and has_x: add(p, '✅', '安装', 'Codex 插件市场结构齐全')
            elif has_x or xm: add(p, '❌', '安装', '缺 .agents/plugins/marketplace.json 或 .codex-plugin/plugin.json，Codex 装不上')
            else: add(p, '❌', '安装', '没有 Codex 插件结构（.agents/plugins/marketplace.json + .codex-plugin/plugin.json）')
        else:
            if cm: add(p, '✅', '安装', 'Claude 插件市场结构齐全（终端、桌面 app、Cowork 共用）')
            else: add(p, '❌', '安装', '没有 .claude-plugin/marketplace.json，只能手动复制，装不上也收不到更新')
        if readme and not re.search(MENTION[p], readme):
            add(p, '⚠️', 'README', f'README 没提 {NAMES[p]} 怎么装 / 怎么用')

    skills = find_skills(root)
    if not skills:
        print('没找到 SKILL.md'); print('STATUS=FAIL'); sys.exit(1)
    for sk in skills:
        name = os.path.basename(sk)
        md = read(os.path.join(sk, 'SKILL.md'))
        local = {os.path.splitext(f)[0] for f in os.listdir(os.path.join(sk, 'scripts'))} if os.path.isdir(os.path.join(sk, 'scripts')) else set()
        texts = [(os.path.join(sk, 'SKILL.md'), md)] + [(f, t) for f in code_files(sk) if 'platform-check: skip-file' not in (t := read(f))]
        domains, gpu_hits, mac_hits, deps, py2 = {}, [], [], [], []
        for f, t in texts:
            rel = os.path.relpath(f, root)
            lines = t.splitlines()
            for i, line in enumerate(lines):
                if re.search(MAC_ONLY, line):
                    ctx = '\n'.join(lines[max(0, i - 8): i + 3])
                    if not re.search(FALLBACK, ctx):
                        mac_hits.append(f'{rel}:{i + 1}')
                if re.search(GPU, line, re.I) and 'disable-gpu' not in line:
                    gpu_hits.append(f'{rel}:{i + 1}')
                for d in re.findall(r'https?://([A-Za-z0-9.-]+\.[A-Za-z]{2,})', line):
                    if d not in ('127.0.0.1', 'localhost') and not d.endswith('.example.com'):
                        domains.setdefault(d, rel)
            if f.endswith('.py'):
                mods = third_party_py(f, local)
                if mods and not re.search(r'pip.{0,40}install|--target', t):
                    deps.append(f'{rel} 要 {",".join(mods)}')
        for m in re.finditer(r'`[^`]*\bpython (?!3)[^`]*`', md):
            py2.append(m.group(0)[:50])

        # 2. 跑得起来吗
        for p in plats:
            sb = p in SANDBOX
            if mac_hits:
                add(p, '❌' if sb else '⚠️', f'{name} 只认 Mac', f'{len(mac_hits)} 处只在 Mac 能用、没写别的系统怎么办：{"、".join(mac_hits[:4])}')
            if gpu_hits and sb:
                add(p, '⚠️', f'{name} 显卡', f'用到显卡加速（{"、".join(gpu_hits[:3])}），沙盒里没有显卡，要有 CPU 退路')
            if deps:
                add(p, '❌', f'{name} 依赖', '用到第三方包但没有自动安装：' + '；'.join(deps[:3]))
            if py2 and p in ('cowork', 'codex', 'claude-code'):
                add(p, '⚠️', f'{name} python', f'命令写的是 python 不是 python3，Linux 上可能没有：{py2[0]}')
            for d, rel in domains.items():
                if KNOWN_BLOCKED.get(d) == p:
                    add(p, '❌', f'{name} 网络', f'{rel} 要访问 {d}，{NAMES[p]} 实测会拦，换个下载源')
            if sb and domains and not re.search(NET_HELP, md):
                add(p, '⚠️', f'{name} 网络', f'要上网（{"、".join(list(domains)[:4])}），SKILL.md 没写网络被拦时怎么跟用户说')
            desk = [l for l in md.splitlines() if re.search(r'~/Desktop|桌面上|到用户桌面|另存.{0,6}桌面|存.{0,4}到桌面', l)]
            if sb and any(not re.search(r'沙盒|Cowork|Codex|写不了|不能写|能写桌面就', l) for l in desk):
                add(p, '⚠️', f'{name} 文件位置', f'{NAMES[p]} 只能碰用户给的文件夹，写到桌面会失败，要有退路（放回用户文件夹）')
            if re.search(r'浏览器|browser|侧边|网页|页面', md):
                # 有专门讲「在哪打开」的小节，就只在那一节里找平台名
                secs = re.findall(r'^#+ [^\n]*(?:打开|浏览器|browser|Browser)[^\n]*\n(.*?)(?=^#+ |\Z)', md, re.M | re.S)
                where = '\n'.join(secs) or md
                if not re.search(MENTION[p], where):
                    add(p, '⚠️', f'{name} 交互', f'要打开页面让用户点，{"「在哪打开」那一节" if secs else "SKILL.md"}没写在 {NAMES[p]} 里怎么打开')

    # 输出
    for p in plats:
        mine = [r for r in rows if r[0] == p]
        worst = '❌' if any(r[1] == '❌' for r in mine) else '⚠️' if any(r[1] == '⚠️' for r in mine) else '✅'
        print(f'\n## {worst} {NAMES[p]}')
        for _, lvl, item, msg in mine:
            print(f'{lvl} {item}：{msg}')
    fail = any(r[1] == '❌' for r in rows); warn = any(r[1] == '⚠️' for r in rows)
    print('\n静态体检只能查出写法问题；沙盒网络白名单、真机交互要在该平台真跑一次才算数。')
    print('STATUS=' + ('FAIL' if fail else 'WARN' if warn else 'PASS'))
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
