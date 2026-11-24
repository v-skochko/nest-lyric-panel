"""Exercise both visual editors and preserve nested configuration."""
import json
import os
import re
import subprocess
from pathlib import Path
fixture = (Path(__file__).parent / 'editor_test.html').resolve().as_uri()
html = subprocess.run([os.environ['CHROME'], '--headless', '--disable-gpu', '--no-sandbox', '--allow-file-access-from-files', '--virtual-time-budget=1500', '--dump-dom', fixture], check=True, capture_output=True, text=True).stdout
match = re.search(r'<pre id="result">(.*?)</pre>', html)
assert match and match.group(1) != 'waiting', 'Editor did not initialize'
r = json.loads(match.group(1))
assert r['sections'] == ['Джерело', 'Лірика та синхронізація', 'Вигляд']
assert r['font'] == 38 and r['preserved'] and r['changed'] == 'media_player.changed' and r['added']
assert r['web'] == 27 and r['webEntity'] == 'media_player.x'
assert r['displayFactory'] == r['lyricFactory'] == 'nest-lyric-editor'
print('Visual editors: configurations, room mapping and preservation verified')
