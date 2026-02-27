# Pčela – Android aplikacija

WebView aplikacija koja otvara TVI Pčela web aplikaciju (evidencija radnog vremena).

## Zahtevi

- Android Studio (Ladybug ili noviji) ili Android SDK + Gradle
- JDK 17

## URL aplikacije

Pre builda postavi URL web aplikacije u **app/src/main/res/values/strings.xml**:

```xml
<string name="app_url">https://tvoj-tunnel.trycloudflare.com</string>
```

Zameni sa stvarnom adresom (Cloudflare tunnel ili server gde radi Pčela).

## Build (APK)

**Iz Android Studio:** Otvori folder `android-app`, pa Build → Build Bundle(s) / APK(s) → Build APK(s). Release: Build → Generate Signed Bundle / APK.

**Iz komandne linije** (potreban Gradle wrapper u projektu):
```bash
cd android-app
./gradlew assembleRelease   # Linux/macOS
gradlew.bat assembleRelease # Windows
```

APK se nalazi u: **app/build/outputs/apk/release/app-release.apk**

Za instalaciju na uređaj potreban je potpisan APK (debug build je potpisan automatski; za release dodaj signing u app/build.gradle.kts).

## Postavljanje APK-a za preuzimanje sa weba

1. Izgradi release APK (gore).
2. Kopiraj `app-release.apk` u root projekta Pčela (bee) kao **Pcela.apk**, ili ga ostavi na putanji `android-app/app/build/outputs/apk/release/app-release.apk`.
3. Ikona za preuzimanje u web aplikaciji (📱) servira APK sa `/api/download-app`.

## Debug build (brži, za testiranje)

```bash
./gradlew assembleDebug
```

APK: **app/build/outputs/apk/debug/app-debug.apk**
