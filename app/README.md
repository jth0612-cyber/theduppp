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

## 4. 푸시 알림 켜기 (Firebase 클라우드 메시징, 무료·건수 제한 없음)

코드는 다 들어가 있습니다. 아래 파일 세 개만 넣으면 켜집니다. 파일이 없으면 앱·사이트는 알림 없이 그대로 동작합니다.

1. console.firebase.google.com 에서 프로젝트 만들기(애널리틱스는 꺼도 됨).
2. **안드로이드 앱 추가**: 패키지 이름 `me.synology.jth4377.lab` → `google-services.json` 을 받아 `app/android/app/` 에 넣고 다시 빌드.
3. **iOS 앱 추가**: 번들 ID `me.synology.jth4377.lab` → `GoogleService-Info.plist` 를 받습니다.
   - Apple Developer → Keys 에서 **APNs 키(.p8)** 를 만들어 Firebase 프로젝트 설정 → 클라우드 메시징 → Apple 앱 구성에 올립니다.
   - Apple Developer → Identifiers → 이 앱 ID 에 **Push Notifications** 를 켭니다.
   - plist 를 base64 로 바꿔(`[Convert]::ToBase64String([IO.File]::ReadAllBytes("GoogleService-Info.plist"))`) Codemagic 환경 변수 `GOOGLE_SERVICE_INFO_PLIST` 로 넣습니다. 없으면 Codemagic 이 알림 없이 빌드합니다.
4. **서버 키**: Firebase 프로젝트 설정 → 서비스 계정 → 새 비공개 키 생성 → 받은 JSON 을 NAS 의 `docker/student-lms/instance/firebase.json` 으로 올립니다(File Station). 저장소·zip 에는 넣지 않습니다.

그 뒤로는 사이트가 웹 푸시를 보내는 모든 곳(새 공지, 질문 답변, 첨삭·피드백 등)에서 앱 알림도 같이 나갑니다. 앱은 로그인한 뒤 알림 권한을 묻고 기기 토큰을 서버(`/push/app-token`)에 등록합니다. 알림을 누르면 그 화면이 열리고, 로그아웃하면 그 기기 토큰을 지웁니다.

## 5. 심사 전 점검 (2026-11-27)

기준: 오픈소스 점검표 `mjmirza/app-store-compliance`(심사 반려 유형 124가지)의 체크리스트와 Capacitor 문서. 그 저장소의 스크립트를 설치해 돌린 것은 아니고, 항목을 읽어 이 앱에 해당하는 것을 손으로 확인했다.

갖춘 것
- 안드로이드 대상 SDK 36 (`android/variables.gradle`). 권한은 인터넷과 알림뿐.
- 개인정보처리방침과 이용약관이 앱 안에서 열린다 (사이트 맨 아래, 가입 화면).
- 아이폰: 카메라와 사진 보관함 사용 이유(`NSCameraUsageDescription`, `NSPhotoLibraryUsageDescription`), 암호화 신고 값(`ITSAppUsesNonExemptEncryption` = false)을 `ios/App/App/Info.plist`에 넣음. 사진을 올리는 화면에서 이유 문구가 없으면 앱이 꺼진다.
- 안드로이드 `allowBackup`을 껐다 (로그인 정보가 기기 백업에 들어가지 않게).
- 계정 삭제(애플 5.1.1(v), 구글): 계정 화면에서 비밀번호를 확인하고 바로 삭제한다. 로그인 계정과 앱 활동만 지우고 성적, 출결, 올린 질문은 학원 기록으로 남긴다(운영자 결정). 스토어에 적을 공개 주소는 `/account-deletion`. 성적까지 지우는 길은 같은 화면의 개인정보 삭제 요청.
- 질답 게시판 신고와 차단(애플 1.2): 남의 글에 신고와 '이 학생 글 안 보기'. 신고한 학생에게는 바로 안 보이고, 조교와 선생님이 질문 목록의 신고 표시를 보고 숨기거나 문제 없음으로 닫는다. 약관에 금지 내용과 24시간 안 확인을 적음.

아직 없어서 반려될 수 있는 것
- 아이폰 개인정보 매니페스트(`PrivacyInfo.xcprivacy`): 앱 것이 없다. Xcode 프로젝트에 파일을 넣어야 해서 맥이나 Codemagic 빌드 단계에서 추가한다.
- 웹을 감싼 앱(애플 4.2): 웹사이트를 그대로 띄우기만 하면 반려 사유다. 푸시 알림과 오프라인 화면이 있다는 점, 로그인 뒤 기능을 심사 메모에 적는다.

제출할 때 챙길 것
- 심사용 계정과 가입 코드, 기능까지 가는 길을 심사 메모에 적는다. 심사 기간에는 사이트가 계속 켜져 있어야 한다.
- 스토어의 개인정보 항목(애플 개인정보 라벨, 구글 데이터 보안 설문)을 실제 수집과 맞춘다: 이름, 아이디, 성적, 올린 사진, 기기 알림 토큰(Firebase).
- 스크린샷은 로그인 화면이 아니라 로그인한 뒤 화면으로. 연령 등급 설문.
- 구글 개인 계정은 비공개 테스트 12명, 14일.

## 남은 일

- Google 로그인을 켜 둔 경우: 구글은 앱 안 웹뷰 로그인을 막으므로, 앱에서는 시스템 브라우저로 로그인하고 돌아오게 해야 합니다.
