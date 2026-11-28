import json, os, re, subprocess
from pathlib import Path
url=(Path(__file__).parent/'theme_fit_test.html').resolve().as_uri()
out=subprocess.run([os.environ['CHROME'],'--headless','--disable-gpu','--no-sandbox','--allow-file-access-from-files','--virtual-time-budget=1500','--dump-dom',url],check=True,capture_output=True,text=True).stdout
m=re.search(r'<pre id="result">(.*?)</pre>',out)
assert m and m.group(1) != 'waiting'
r=json.loads(m.group(1))
assert r['theme']=='dark' and r['shortSize']>r['longSize'] and r['longSize']==12, r
assert r['wrap']=='nothing but to hold but tight\nand more words', r
assert 'no-timestamps' in r['view']
assert len(r['rows']) > 1 and all(x['width'] <= x['available']+1 for x in r['rows']), r
assert len(set(x['size'] for x in r['rows'])) > 1, r
print('Dark theme, compact wrapping and readable fallback verified')
