#!/usr/bin/env bash
# lms 코드를 데모 폴더로 복사하고 로컬 데모 서버(127.0.0.1:5077)를 다시 켠다. Git Bash 에서 실행.
#   bash tools/demo_resync.sh
# 데모 DB(_deploy/demo/student-lms-demo/instance/)는 건드리지 않는다.
M="$(cd "$(dirname "$0")/.." && pwd)"
D="$M/_deploy/demo/student-lms-demo"
cp -r "$M/lms/templates" "$M/lms/static" "$M/lms/views" "$D/" && cp "$M"/lms/*.py "$D/"
pid=$(netstat -ano | grep "127.0.0.1:5077.*LISTEN" | awk '{print $NF}' | head -1)
[ -n "$pid" ] && taskkill //PID "$pid" //F >/dev/null 2>&1
cd "$D" && ("$M/lms/.venv/Scripts/python" -X utf8 -c "from app import create_app; from waitress import serve; serve(create_app(), host='127.0.0.1', port=5077)" > /tmp/demo_srv.log 2>&1 &)
sleep 5; curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5077/login
