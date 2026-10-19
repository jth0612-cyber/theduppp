#!/bin/sh
# hwp -> hwpx 변환기(neolord0/hwp2hwpx) 빌드. JDK 8+ / Maven 필요.
# 사용: ./build_hwp2hwpx.sh <작업폴더>  → <작업폴더>/hwp2hwpx.sh in.hwp out.hwpx
set -e
W=${1:-./conv}; T=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$W" && cd "$W"
[ -d hwp2hwpx ] || git clone -q --depth 1 https://github.com/neolord0/hwp2hwpx.git
O="-q -Dmaven.test.skip=true -Dmaven.compiler.source=8 -Dmaven.compiler.target=8 -Dmaven.javadoc.skip=true -Dgpg.skip"
# hwplib/hwpxlib 는 Maven Central 에서 받아옴
(cd hwp2hwpx && sed -i 's#<source>1\?\.\?[67]</source>#<source>8</source>#; s#<target>1\?\.\?[67]</target>#<target>8</target>#' pom.xml && mvn $O package dependency:copy-dependencies)
mkdir -p cli && javac -cp "hwp2hwpx/target/hwp2hwpx-1.0.0.jar:hwp2hwpx/target/dependency/*" -d cli "$T/HwpToHwpx.java"
cat > hwp2hwpx.sh <<'X'
#!/bin/sh
D=$(dirname "$0")
java -cp "$D/cli:$D/hwp2hwpx/target/hwp2hwpx-1.0.0.jar:$D/hwp2hwpx/target/dependency/*" HwpToHwpx "$1" "$2" 2>&1 | { grep -v JAVA_TOOL || true; }
X
chmod +x hwp2hwpx.sh
echo "ok: $W/hwp2hwpx.sh"
