import json, os, re, subprocess
from pathlib import Path
fixture = (Path(__file__).parent / 'layout_test.html').resolve().as_uri()
html = subprocess.run([os.environ['CHROME'], '--headless', '--disable-gpu', '--no-sandbox', '--allow-file-access-from-files', '--window-size=1400,800', '--virtual-time-budget=3000', '--dump-dom', fixture], check=True, capture_output=True, text=True).stdout
match = re.search(r'<pre id="result">(.*?)</pre>', html)
assert match and match.group(1) != 'waiting', 'Layout did not initialize'
r = json.loads(match.group(1))
for mode in ('column', 'compact', 'wide'):
    assert r[mode]['mode'] == mode and r[mode]['child'] == mode, r
assert r['column']['cover'] == 'none' and r['column']['height'] == 320, r
assert r['compact']['cover'] != 'none' and r['wide']['cover'] != 'none', r
assert r['forced']['mode'] == 'compact' and r['forced']['child'] == 'compact', r
assert r['choices'] == ['auto', 'column', 'compact', 'wide'] and r['emitted'] == 'wide', r
for label in ('Стиль Nest', 'Підганяти текст', 'Розмір тексту, px', 'Розмір перекладу, px'):
    assert label not in r['labels'], r
print('Container resize, manual override, child styles and editor verified')
