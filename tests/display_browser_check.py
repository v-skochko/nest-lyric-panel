"""Run the full display against a fake Home Assistant in Chromium."""
import json
import os
import re
import subprocess
from pathlib import Path

chrome = os.environ["CHROME"]
fixture = (Path(__file__).parent / "display_test.html").resolve().as_uri()
for width in (600, 768, 1024, 1400):
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
    assert result["youtubeTimeline"] == result["youtubeLyricEntity"] == "media_player.b_cast"
    assert result["youtubeElapsed"] == "0:40" and result["pausedElapsed"] == "0:45"
    assert result["pausedTimeline"] == "media_player.b_cast" and result["backToMusic"] == "media_player.b_ma"
    assert result["singlePlayer"] == "media_player.a_ma"
    assert [(c["service"], c["data"]["entity_id"]) for c in result["calls"]] == [
        ("media_next_track", "media_player.a_ma"),
        ("volume_up", "media_player.b_speaker"),
        ("media_play_pause", "media_player.b_speaker"),
        ("media_next_track", "media_player.b_speaker"),
    ]
    assert result["buttonOrder"] == ["volume_down", "media_previous_track", "media_play_pause", "media_next_track", "volume_up"]
    assert result["centerDelta"] < 1 and result["playWidth"] > result["otherWidth"]
    assert result["playColor"] == "rgb(29, 185, 84)" and result["volumeColors"] == ["rgb(211, 227, 253)"] * 2
    assert result["elapsed"] == "0:40" and result["duration"] == "1:40"
    assert result["progressRole"] == "progressbar" and result["progressValue"] == "40"
    assert result["progressFocusable"] is False and result["sliderCount"] == 0
    assert 0 <= result["progressGap"] <= 10
    assert result["unknownElapsed"] == "—:—" and result["unknownValue"] is None and not result["unknownActive"]
    assert result["newTrackTitle"] == "Track Changed" and result["newTrackElapsed"] == "0:05"
    print(f"{width}px: player selection, centred controls and read-only progress verified")
