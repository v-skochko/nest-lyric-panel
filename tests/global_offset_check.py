"""Check global offset loading and live settings refresh."""
import json,os,re,subprocess
from pathlib import Path
path=(Path(__file__).parent/'global_offset_test.html').resolve().as_uri()
out=subprocess.run([os.environ['CHROME'],'--headless','--disable-gpu','--no-sandbox','--allow-file-access-from-files','--virtual-time-budget=1500','--dump-dom',path],check=True,capture_output=True,text=True).stdout
m=re.search(r'<pre id="result">(.*?)</pre>',out);assert m and json.loads(m.group(1))=={'first':1,'next':-2}
print('Global offset initial load and live refresh verified')
