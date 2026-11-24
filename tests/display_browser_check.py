"""Run the full display against a fake Home Assistant in Chromium."""
import json
import os
import re
import subprocess
from pathlib import Path

chrome = os.environ["CHROME"]
fixture = (Path(__file__).parent / "display_test.html").resolve().as_uri()
for width in (1024, 1400):
    html = subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files", f"--window-size={width},800", "--virtual-time-budget=1500", "--dump-dom", fixture],
        check=True, capture_output=True, text=True,
    ).stdout
    match = re.search(r'<pre id="result">(.*?)</pre>', html)
    assert match and match.group(1) != "waiting", "Display did not initialise"
    result = json.loads(match.group(1))
    assert result["initialPlayer"] == "media_player.a_ma" and result["initialTitle"] == "Track A"
    assert result["lyricTag"] == "NEST-LYRIC-PANEL-CARD" and result["lyricOffset"] == 1
    assert result["roomPlayer"] == "media_player.b_ma"
    assert result["youtubePlayer"] == "media_player.b_speaker" and result["youtubeTitle"] == "Track B Cast"
    assert result["singlePlayer"] == "media_player.a_ma"
    assert [(c["service"], c["data"]["entity_id"]) for c in result["calls"]] == [
        ("media_next_track", "media_player.a_ma"),
        ("volume_up", "media_player.b_speaker"),
        ("media_seek", "media_player.b_speaker"),
    ]
    assert result["calls"][-1]["data"]["seek_position"] == 50
    print(f"{width}px: display, room/source selection, controls and seek verified")
