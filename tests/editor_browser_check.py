"""Exercise the simplified editor and preservation of legacy configuration."""
import html, json, os, re, subprocess
from pathlib import Path
fixture=(Path(__file__).parent/'editor_test.html').resolve().as_uri()
out=subprocess.run([os.environ['CHROME'],'--headless','--disable-gpu','--no-sandbox','--allow-file-access-from-files','--virtual-time-budget=1500','--dump-dom',fixture],check=True,capture_output=True,text=True).stdout
m=re.search(r'<pre id="result">(.*?)</pre>',out);assert m and m.group(1)!='waiting'
r=json.loads(html.unescape(m.group(1)));assert r['sections']==['Джерело','Лірика та синхронізація','Вигляд'];assert r['expanders']==0 and r['preserved'] and r['changed']=='media_player.changed';assert 'Висота в режимі колонки' in r['labels'];assert 'Зміщення синхронізації, с' not in r['labels'];assert r['displayFactory']=='nest-lyric-editor'
print('Simplified editor and legacy preservation verified')
