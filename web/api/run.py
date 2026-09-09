"""Vercel serverless function: compile/run a Slang program and return the
output, AST, bytecode disassembly, or transpiled C.

POST {"source": "...", "mode": "run|ast|bytecode|c"} -> {"ok": bool, "text": str}
"""

from http.server import BaseHTTPRequestHandler
import json
from pprint import pformat

from slang import compile_source, optimize, parse, to_c
from slang.bytecode import disassemble
from slang.errors import SlangError
from slang.vm import VM, SlangRuntimeError

MAX_SOURCE = 20_000
MAX_STEPS = 2_000_000


def render(source: str, mode: str) -> dict:
    if len(source) > MAX_SOURCE:
        return {"ok": False, "text": f"source too long (limit {MAX_SOURCE} chars)"}
    try:
        program = optimize(parse(source))
        if mode == "ast":
            return {"ok": True, "text": pformat(program, width=88)}
        if mode == "bytecode":
            return {"ok": True, "text": disassemble(compile_source(program))}
        if mode == "c":
            return {"ok": True, "text": to_c(program)}
        vm = VM(compile_source(program))
        vm.run(max_steps=MAX_STEPS)
        return {"ok": True, "text": vm.stdout.getvalue() or "(program produced no output)"}
    except SlangError as e:
        return {"ok": False, "text": e.render(source)}
    except SlangRuntimeError as e:
        return {"ok": False, "text": f"runtime error: {e}"}
    except RecursionError:
        return {"ok": False, "text": "recursion too deep"}
    except Exception as e:  # noqa: BLE001 - surface anything else to the user
        return {"ok": False, "text": f"{type(e).__name__}: {e}"}


class handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        self._send(204, {})

    def do_POST(self):  # noqa: N802
        try:
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"ok": False, "text": "bad request body"})
        self._send(200, render(str(data.get("source", "")), str(data.get("mode", "run"))))

    def do_GET(self):  # noqa: N802
        self._send(200, {"ok": True, "text": "POST {source, mode} here"})
