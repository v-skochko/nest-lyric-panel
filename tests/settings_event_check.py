"""Ensure integration settings changes reload the current track."""
import json, os, re, subprocess
from pathlib import Path
p=(Path(__file__).parent/'settings_event_test.html').resolve().as_uri()
h=subprocess.run([os.environ['CHROME'],'--headless','--disable-gpu','--no-sandbox','--allow-file-access-from-files','--virtual-time-budget=1500','--dump-dom',p],check=True,capture_output=True,text=True).stdout
m=re.search(r'<pre id="result">(.*?)</pre>',h); assert m and m.group(1)!='waiting'
r=json.loads(m.group(1));assert r=={'first':1,'next':2,'removed':1},r
print('Integration setting event reload and unsubscribe verified')
