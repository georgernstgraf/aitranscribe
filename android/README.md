# AITranscribe - Android App

Native Android version of AITranscribe for F-Droid distribution.

## Tech Stack

- **Language**: Kotlin
- **UI**: Jetpack Compose (Material 3)
- **Database**: Room (SQLite)
- **DI**: Hilt
- **Networking**: Retrofit + OkHttp
- **Background**: WorkManager

## Building

```bash
cd android
./gradlew assembleDebug
./gradlew assembleRelease
```

## Testing

```bash
cd android
./gradlew test
./gradlew connectedAndroidTest
```

## Notes

- Package: `com.georgernstgraf.aitranscribe`
- Min SDK: 26 (Android 8.0)
- Target SDK: 34 (Android 14)
- All libraries are FOSS for F-Droid compatibility
