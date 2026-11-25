# 통합과학 lab 앱 (안드로이드·아이폰)

실제 사이트 `https://lab.jth4377.synology.me` 를 그대로 띄우는 Capacitor 8 앱입니다. 화면·데이터는 사이트와 하나라, 사이트를 업데이트하면 앱도 바로 바뀝니다(스토어 재심사 없음). 앱을 다시 올려야 하는 때는 아이콘·이름·네이티브 기능을 바꿀 때뿐입니다.

- 앱 ID: `me.synology.jth4377.lab` / 이름: 통합과학 lab
- 설정: `capacitor.config.json` (사이트 주소, 연결이 끊겼을 때 보여 줄 `www/offline.html`, 사용자 에이전트 `THeduApp/1.0`)
- 사이트는 사용자 에이전트로 앱을 알아보고(`lms/static/inapp.js` → `html.in-app`), 앱 안에서는 웹 푸시 버튼을 감춥니다.
- 아이콘·시작 화면 원본: `assets/` (다시 만들기: `npx capacitor-assets generate --android --ios`)

## 1. 이 PC에서 안드로이드 빌드

설치돼 있는 것: Microsoft OpenJDK 21, Android SDK (`%LOCALAPPDATA%\Android\Sdk`, 환경 변수 `JAVA_HOME`·`ANDROID_HOME`).

```powershell
cd app; npm install; npx cap sync android
cd android; .\gradlew.bat assembleDebug      # 시험용: android\app\build\outputs\apk\debug\app-debug.apk
cd android; .\gradlew.bat bundleRelease      # 플레이 스토어용: android\app\build\outputs\bundle\release\app-release.aab
```

**출시 서명 키**: `android/thedu-upload.jks` + `android/keystore.properties` (비밀번호). 저장소에는 올리지 않습니다. 반드시 다른 곳(USB 등)에 백업하세요. 구글 플레이 앱 서명을 쓰면 이 키를 잃어도 구글에 재설정을 요청할 수 있지만 며칠 걸립니다.

## 2. 구글 플레이 올리기 (등록비 한 번 25달러)

1. Google Play Console 가입(개발자 등록) → 앱 만들기(이름 '통합과학 lab', 무료, 앱).
2. 개인 계정이면 정식 출시 전 **비공개 테스트에 테스터 12명 이상, 14일 이상**이 필요합니다(구글 정책). 조교·학생 계정(Gmail)을 테스터 목록에 넣고 테스트 링크를 나눠 줍니다.
3. 테스트 트랙에 `app-release.aab` 를 올립니다. 버전을 올릴 때마다 `android/app/build.gradle` 의 `versionCode` 를 1씩 올립니다.
4. 스토어 등록정보: 짧은 설명, 자세한 설명, 아이콘 512px(`assets/icon-only.png` 를 줄여 씀), 휴대폰 스크린샷 2장 이상, 개인정보처리방침 주소, 데이터 보안 설문(이름·아이디·성적 수집, 전송 시 암호화, 삭제 요청 가능).

## 3. 아이폰 올리기 (애플 개발자 매년 99달러, 맥 없이 Codemagic 으로 빌드)

1. Apple Developer Program 가입 → App Store Connect 에서 앱 만들기(번들 ID `me.synology.jth4377.lab`).
2. App Store Connect → 사용자 및 액세스 → 통합 → **App Store Connect API 키** 만들기(역할: App Manager). 키 파일(.p8)·Issuer ID·Key ID 를 받습니다.
3. Codemagic(codemagic.io) 가입 → 이 GitHub 저장소 추가 → Team settings → Integrations → App Store Connect 에 2번 키를 넣고 이름을 `THEDU_ASC` 로 저장.
4. 앱의 Apple ID(숫자, App Store Connect 앱 정보)를 Codemagic 환경 변수 `APP_STORE_APPLE_ID` 로 넣습니다.
5. Start new build → 워크플로 `ios-testflight` (설정: 저장소 맨 위 `codemagic.yaml`). 끝나면 TestFlight 에 올라가 휴대폰에서 시험할 수 있습니다. 무료 한도: macOS M2 월 500분, 한 번에 10~15분.
6. 심사 제출 시 '로그인이 필요한 앱'이므로 심사용 계정(데모 사이트 학생 계정 등)과 설명을 적습니다.

## 남은 일

- 네이티브 푸시 알림 (Firebase 클라우드 메시징, 무료): Firebase 프로젝트를 만든 뒤 `google-services.json`(안드로이드)·APNs 키(아이폰)를 받아 붙입니다.
- 앱 홈 화면을 확정 시안(`docs/app_design/README.md`, `소개자료_사진/홈과_기능별/`)대로.
- Google 로그인을 켜 둔 경우: 구글은 앱 안 웹뷰 로그인을 막으므로, 앱에서는 시스템 브라우저로 로그인하고 돌아오게 해야 합니다.
