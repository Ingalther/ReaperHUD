"""update.bat's window in the HUD's colours: turquoise text (update.bat: color 0B), the lines that report a problem
red, the ones that report something done or fine green. Only in a console window: a redirected output stays plain."""
import os
import re
import sys

RED, GREEN, CYAN, OFF = '\x1b[91m', '\x1b[92m', '\x1b[96m', '\x1b[0m'
BAD = re.compile(r'^\s*(!!|WARNING|ERROR|Traceback|\d+ problem\(s\))|could not|Could not|failed|is missing', re.I)
GOOD = re.compile(r'^\s*(OK\b|built ->|installed ->|No problems)')


class _Coloured:
    def __init__(self, out):
        self.out, self.rest = out, ''

    def write(self, text):
        self.rest += text
        *whole, self.rest = self.rest.split('\n')
        for line in whole:
            tint = RED if BAD.search(line) else GREEN if GOOD.search(line) else CYAN
            self.out.write(f'{tint}{line}{OFF}\n')
        return len(text)

    def flush(self):
        if self.rest:
            self.out.write(CYAN + self.rest + OFF)
            self.rest = ''
        self.out.flush()

    def __getattr__(self, name):
        return getattr(self.out, name)


def colours():
    if os.name != 'nt' or not sys.stdout.isatty():
        return
    os.system('')   # Windows 10+: turns the console's colour codes on
    sys.stdout = _Coloured(sys.stdout)
    sys.stderr = _Coloured(sys.stderr)
