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
        [chrome, "--headless", "--disable-gpu", "--no-sandbox", f"--window-size={width},800", "--virtual-time-budget=1000", "--dump-dom", fixture],
        check=True, capture_output=True, text=True,
    ).stdout
    match = re.search(r'<pre id="result">(.*?)</pre>', html)
    assert match, "Fixture did not produce results"
    data = json.loads(match.group(1))
    assert data["nest"]["width"] == width
    for key in ("nest", "uk"):
        item = data[key]
        if width <= 1124:
            assert abs(item["firstFont"] - item["secondFont"]) < 0.1
            assert item["whiteSpace"] == "normal" and item["secondHeight"] > item["lineHeight"] * 2
            assert item["transform"] == "none"
            assert item["translationWhiteSpace"] == "nowrap"
            assert item["translationY"] >= item["originalBottom"]
        else:
            assert item["whiteSpace"] == "nowrap" and item["firstFont"] > item["secondFont"] * 2
    assert data["web"]["whiteSpace"] == "nowrap" and data["plain"]["unsynced"]
    print(f"{width}px: verified")
