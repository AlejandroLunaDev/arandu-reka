"""Serve the repo for the Arandu fur preview and save its renders.

    python blender/arandu/preview/server.py
    open http://127.0.0.1:8765/blender/arandu/preview/

POST /render/<name> with a PNG body writes blender/arandu/renders/<name>.png.
"""

import http.server
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
RENDERS = os.path.normpath(os.path.join(HERE, "..", "renders"))


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".glb": "model/gltf-binary",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=REPO, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        name = os.path.basename(self.path[len("/render/"):]) if self.path.startswith("/render/") else ""
        if not name:
            self.send_error(404)
            return
        os.makedirs(RENDERS, exist_ok=True)
        size = int(self.headers.get("Content-Length", 0))
        with open(os.path.join(RENDERS, name + ".png"), "wb") as out:
            out.write(self.rfile.read(size))
        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
