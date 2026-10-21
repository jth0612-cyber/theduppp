"""Synology 공유 링크(gofile.me) 폴더 목록/다운로드.
Usage:
  python3 synoshare.py ls <sharing_id> <password>            # 전체 트리 출력
  python3 synoshare.py get <sharing_id> <password> <out_dir> [path_prefix_or_glob ...]
"""
import fnmatch, json, os, sys, urllib.parse, urllib.request, http.cookiejar

HOST = os.environ.get("SYNO_HOST", "https://jth4377.synology.me")
API = HOST + "/sharing/webapi/entry.cgi"


class Share:
    def __init__(self, sid, password):
        self.sid = sid
        cj = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        r = self.call(api="SYNO.Core.Sharing.Login", version=1, method="login",
                      sharing_id=json.dumps(sid), password=json.dumps(password), hdr=False)
        if not r.get("success"):
            sys.exit(f"login failed: {r}")
        init = self.call(api="SYNO.Core.Sharing.Initdata", version=1, method="get")
        self.root = "/" + init["data"]["Private"]["filename"]

    def _req(self, params, hdr=True):
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(API, data=data)
        if hdr:
            req.add_header("X-SYNO-SHARING", self.sid)
        return self.op.open(req, timeout=300)

    def call(self, hdr=True, **params):
        return json.load(self._req(params, hdr))

    def ls(self, path):
        out, off = [], 0
        while True:
            r = self.call(api="SYNO.FolderSharing.List", version=2, method="list",
                          _sharing_id=json.dumps(self.sid), folder_path=json.dumps(path),
                          offset=off, limit=1000, additional=json.dumps(["size"]))
            if not r.get("success"):
                raise RuntimeError(f"list {path}: {r}")
            files = r["data"]["files"]
            out += files
            off += len(files)
            if not files or off >= r["data"].get("total", off):
                return out

    def walk(self, path=None):
        for f in self.ls(path or self.root):
            yield f
            if f["isdir"]:
                yield from self.walk(f["path"])

    def download(self, path, dest):
        r = self._req({"api": "SYNO.FolderSharing.Download", "version": 2, "method": "download",
                       "mode": "download", "stdhtml": "false", "_sharing_id": json.dumps(self.sid),
                       "path": json.dumps([path]), "dlname": json.dumps(os.path.basename(path))})
        if "json" in r.headers.get("Content-Type", ""):
            raise RuntimeError(f"download {path}: {r.read()[:200]}")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            while chunk := r.read(1 << 20):
                fh.write(chunk)


def main():
    cmd, sid, pw = sys.argv[1:4]
    s = Share(sid, pw)
    if cmd == "ls":
        for f in s.walk():
            rel = f["path"][len(s.root) + 1:]
            print(("D " if f["isdir"] else "F ") + rel + ("/" if f["isdir"] else f"  {f['additional']['size']}"))
    elif cmd == "get":
        out, pats = sys.argv[4], sys.argv[5:] or ["*"]
        for f in s.walk():
            rel = f["path"][len(s.root) + 1:]
            if f["isdir"] or not any(fnmatch.fnmatch(rel, p) or rel.startswith(p) for p in pats):
                continue
            dest = os.path.join(out, rel)
            if os.path.exists(dest) and os.path.getsize(dest) == f["additional"]["size"]:
                continue
            print("get", rel, f["additional"]["size"], flush=True)
            s.download(f["path"], dest)


if __name__ == "__main__":
    main()
