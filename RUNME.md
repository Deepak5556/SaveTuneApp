# SaveTune Mobile — How To Run

## ❌ WRONG (causes ERR_CONNECTION_REFUSED)
flutter run                    # defaults to web or wrong device
flutter run -d chrome          # web — Go server cannot run here
flutter run -d web-server      # web — same problem
flutter run -d edge            # web — same problem
flutter run -d macos           # desktop — same problem
flutter run -d windows         # desktop — same problem

## ✅ CORRECT
flutter devices                          # step 1: list devices
flutter run -d android                   # step 2: run on Android
flutter run -d <your-device-id>          # or specify exact device

## Build APK (install manually)
# Build Go binary first:
cd savetune-go
CGO_ENABLED=0 GOOS=android GOARCH=arm64 go build -trimpath -ldflags="-s -w" -o ../android/app/src/main/assets/savetune-server .

# Then build APK (from D:\Hexoran\App):
flutter pub get
flutter build apk --release --split-per-abi

# Install on connected Android device:
adb install -r build/app/outputs/flutter-apk/app-arm64-v8a-release.apk

## Debug logs from Go server (while app is running)
adb logcat -s SaveTuneGoService    # see Go server logs
adb logcat -s flutter              # see Flutter logs
