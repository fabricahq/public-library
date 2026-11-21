#!/usr/bin/env python3
"""Keep the 5K skills' shared shell identical in every page.

The 5K skills each install on their own, so each page carries its own copy of
the shell: the fonts, palette, top bar, menu, Settings modal and About dialog.
`sync` writes shell.css, with the fonts inlined, between each page's
`/* 5k-shell:start */` and `/* 5k-shell:end */` markers and copies the font
licenses into each skill's references/. `check` fails when any copy differs.
"""
import base64
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SKILLS = ROOT / '.trailguide' / 'skills' / 'fabrica'
PAGES = {
    '5k-pr-review': 'assets/canvas.html',
    '5k-code-review': 'assets/panel.html',
    '5k-grill-me': 'assets/canvas.html',
}
LICENSES = ('Inter-OFL.txt', 'JetBrainsMono-OFL.txt')
START, END = '/* 5k-shell:start */', '/* 5k-shell:end */'


def block():
    css = (HERE / 'shell.css').read_text()
    for key, name in (('__INTER__', 'inter.woff2'), ('__MONO__', 'jetbrains-mono.woff2')):
        css = css.replace(key, base64.b64encode((HERE / name).read_bytes()).decode())
    return f'{START}\n{css.rstrip()}\n{END}'


def splice(text, new, where):
    a, b = text.find(START), text.find(END)
    if a < 0 or b < a:
        raise SystemExit(f'{where}: missing the {START} ... {END} markers')
    return text[:a] + new + text[b + len(END):]


def main(argv):
    mode = argv[1] if len(argv) > 1 else 'check'
    if mode not in ('sync', 'check'):
        raise SystemExit('usage: shell.py sync|check')
    new, stale = block(), []
    for skill, rel in PAGES.items():
        page = SKILLS / skill / rel
        text = page.read_text()
        want = splice(text, new, page.relative_to(ROOT))
        if want != text:
            stale.append(page.relative_to(ROOT))
            if mode == 'sync':
                page.write_text(want)
        for name in LICENSES:
            dest = SKILLS / skill / 'references' / name
            src = (HERE / name).read_bytes()
            if not dest.exists() or dest.read_bytes() != src:
                stale.append(dest.relative_to(ROOT))
                if mode == 'sync':
                    dest.write_bytes(src)
    if mode == 'check' and stale:
        print('The 5K shell is out of date in:', *stale, sep='\n  ')
        print('Run: python3 .github/scripts/5k-shell/shell.py sync')
        return 1
    print(('Synced' if mode == 'sync' else 'Checked'), len(PAGES), 'pages', f'({len(stale)} updated)' if mode == 'sync' else '')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
