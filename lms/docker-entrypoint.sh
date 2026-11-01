#!/bin/sh
# 데이터 폴더(instance) 소유권을 app 사용자에게 넘긴 뒤, root 가 아닌 app 사용자로 서버를 실행한다.
set -e
mkdir -p /app/instance
chown -R app:app /app/instance
exec setpriv --reuid=app --regid=app --init-groups \
  waitress-serve --listen=0.0.0.0:8000 --threads=8 --call app:create_app
