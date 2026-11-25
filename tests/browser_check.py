"""Optional browser check; set CHROME to a Chromium executable."""
import json
import os
import re
import subprocess
from pathlib import Path

chrome = os.environ["CHROME"]
fixture = (Path(__file__).parent / "browser_test.html").resolve().as_uri()
for width in (1024, 1124, 1125, 1400):
    html = subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files", f"--window-size={width},800", "--virtual-time-budget=1000", "--dump-dom", fixture],
        check=True, capture_output=True, text=True,
    ).stdout
    match = re.search(r'<pre id="result">(.*?)</pre>', html)
    assert match, "Fixture did not produce results"
    data = json.loads(match.group(1))
    assert data["nest"]["width"] == width
    for key, expected in (("nest", 30), ("uk", 30), ("web", 22), ("wide", 38)):
        item = data[key]
        assert item["firstFont"] == item["secondFont"] == expected
        assert item["whiteSpace"] == "normal" and item["transform"] == "none"
        assert item["translationY"] >= item["originalBottom"]
    assert data["plain"]["unsynced"]
    print(f"{width}px: verified")
