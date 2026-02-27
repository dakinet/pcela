# Kako izgraditi Pčela.apk i postaviti na server

## 1. Instaliraj Android Studio

Ako već nemaš: https://developer.android.com/studio  
Prilikom instalacije prihvati i Android SDK.

## 2. Postavi URL u aplikaciji

Otvori fajl **app/src/main/res/values/strings.xml** i zameni URL:

```xml
<string name="app_url">https://TVOJ-CLOUDFLARE-URL.trycloudflare.com</string>
```

(Npr. URL koji dobiješ kad pokreneš `cloudflared tunnel --url http://localhost:7000` na serveru.)

## 3. Izgradi APK u Android Studio

1. Otvori Android Studio → **File → Open** → izaberi folder **android-app** (unutar bee projekta).
2. Sačekaj da se projekat sinhronizuje (Gradle sync).
3. **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
4. Kad se završi, Android Studio ponudi **Locate** – to je tvoj APK.  
   Ili ručno: **android-app/app/build/outputs/apk/debug/app-debug.apk**.

## 4. Postavi APK na server

### Opcija A – skripta (PowerShell)

Iz root-a bee projekta pokreni:

```powershell
.\deploy\deploy-apk.ps1
```

Skripta traži **Pcela.apk** u root-u projekta ili **app-debug.apk** u android-app izlazu, kopira ga na server kao **Pcela.apk** i onda možeš preuzimati preko weba.

### Opcija B – ručno

1. Preimenuj **app-debug.apk** u **Pcela.apk** (ili kopiraj u bee root kao Pcela.apk).
2. Prebaci na server:
   ```text
   pscp -pw neznam123 Pcela.apk root@192.168.0.247:/opt/tvi-bee/
   ```

Posle toga ikona za preuzimanje u web aplikaciji servira **Pcela.apk**.
