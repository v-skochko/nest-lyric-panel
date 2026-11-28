"""Translation cache behavior, including partial and simultaneous requests."""
import ast
import asyncio
import logging
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

source = Path(__file__).resolve().parents[1] / "custom_components/nest_lyric_panel/__init__.py"
tree = ast.parse(source.read_text())
node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "translate")
node.decorator_list = []
scope = {"asyncio": asyncio, "time": time, "DOMAIN": "nest_lyric_panel",
         "is_english": lambda text: True, "_LOGGER": logging.getLogger(__name__)}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), scope)

class Response:
    def __init__(self, lines): self.lines = lines
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    def raise_for_status(self): pass
    async def json(self, **kwargs): return {"translatedText": ["uk:" + line for line in self.lines]}

class Session:
    def __init__(self): self.calls = []
    def post(self, url, *, json, **kwargs):
        self.calls.append(list(json["q"]))
        return Response(json["q"])

class Connection:
    def send_result(self, _, value): self.result = value
    def send_error(self, _, code, message): raise AssertionError((code, message))

class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_partial_concurrent_and_expiry(self):
        session = Session()
        scope["async_get_clientsession"] = lambda hass: session
        shared = {"settings": {"translation_url": "http://translate", "cache_minutes": 60},
                  "translation_cache": {}, "translation_locks": {}}
        hass = SimpleNamespace(data={"nest_lyric_panel": shared})
        async def request(lines):
            conn = Connection()
            await scope["translate"](hass, conn, {"id": 1, "full_text": "same song", "text": lines})
            return conn.result["translatedText"]
        self.assertEqual(await request(["one"]), ["uk:one"])
        self.assertEqual(await request(["one", "two"]), ["uk:one", "uk:two"])
        await asyncio.gather(request(["three"]), request(["three"]))
        self.assertEqual(session.calls, [["one"], ["two"], ["three"]])
        shared["settings"]["cache_minutes"] = 0
        await request(["one"])
        self.assertEqual(session.calls[-1], ["one"])

if __name__ == "__main__": unittest.main()
