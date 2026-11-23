"""wireflow_crawl.js 가 보내는 링크 위치(JSON)를 받아 wireflow/roles3/boxes.json 에 쓰고 끝난다."""
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wireflow", "roles3", "boxes.json")


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        open(OUT, "wb").write(body)
        self.send_response(200); self.end_headers()


HTTPServer(("127.0.0.1", 5099), H).handle_request()
print("saved", OUT)
