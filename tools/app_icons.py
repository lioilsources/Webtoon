#!/usr/bin/env python3
"""Toonfork app icons: the main icon and the alternates (A/B test in the stores + the icon picker in Nastavení).

    cd app && dart run flutter_launcher_icons && cd .. && python3 tools/app_icons.py

(flutter_launcher_icons rewrites the alternate icon names in project.pbxproj, so this script runs after it.)

Sources: app/assets/icon/alt/<key>.png (1024×1024). MAIN becomes app/assets/icon/app_icon.png (+ _fg) for
flutter_launcher_icons. Every key in ALTERNATES gets:
  - iOS:     ios/Runner/Assets.xcassets/AppIcon-<key>.appiconset (single 1024 universal image) and its name in
             ASSETCATALOG_COMPILER_ALTERNATE_APPICON_NAMES (project.pbxproj),
  - Android: an adaptive icon mipmap ic_launcher_<key> (+ legacy PNGs) and an activity-alias .Icon_<key>,
  - Flutter: a 192 px thumbnail assets/icon/thumbs/<key>.png for the picker,
  - Play:    store/play-icon-512-<key>.png (store listing experiments).
PICKER is what Nastavení offers (the main icon first); A/B-only keys are bundled for the App Store test but not
offered. Chosen 2026-11-08: main 11 (stargirl), A/B 15, 18, 21, in the app 18, 16, 21, 12, C, 27, 26, 25.
"""
import json
import re
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
SRC = APP / "assets/icon/alt"
MAIN = "stargirl"
ALTERNATES = ["noirboy", "noirgirl", "comicgirl", "noirboy2", "stargirl2", "classic", "panelsstar", "panelsnoir2",
              "panelsnoir"]
AB = ["noirboy", "noirgirl", "comicgirl"]
PICKER = [MAIN, "noirgirl", "noirboy2", "comicgirl", "stargirl2", "classic", "panelsstar", "panelsnoir2", "panelsnoir"]
BG = "#121212"
DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def img(key):
    return Image.open(SRC / f"{key}.png").convert("RGB").resize((1024, 1024), Image.LANCZOS)


def main_icon():
    im = img(MAIN)
    im.save(APP / "assets/icon/app_icon.png")
    im.save(APP / "assets/icon/app_icon_fg.png")  # full bleed: the adaptive mask keeps the centre
    im.resize((512, 512), Image.LANCZOS).save(ROOT / "docs/icon.png")
    im.resize((512, 512), Image.LANCZOS).save(ROOT / "store/play-icon-512.png")


def ios():
    xc = APP / "ios/Runner/Assets.xcassets"
    for d in xc.glob("AppIcon-*.appiconset"):
        shutil.rmtree(d)
    for key in ALTERNATES:
        d = xc / f"AppIcon-{key}.appiconset"
        d.mkdir()
        img(key).save(d / f"icon-{key}-1024.png")
        (d / "Contents.json").write_text(json.dumps({
            "images": [{"filename": f"icon-{key}-1024.png", "idiom": "universal", "platform": "ios",
                        "size": "1024x1024"}],
            "info": {"author": "xcode", "version": 1}}, indent=2) + "\n")
    pbx = APP / "ios/Runner.xcodeproj/project.pbxproj"
    names = " ".join(f"AppIcon-{k}" for k in ALTERNATES)
    s = re.sub(r'ASSETCATALOG_COMPILER_ALTERNATE_APPICON_NAMES = [^;]*;',
               f'ASSETCATALOG_COMPILER_ALTERNATE_APPICON_NAMES = "{names}";', pbx.read_text())
    s = re.sub(r'ASSETCATALOG_COMPILER_INCLUDE_ALL_APPICON_ASSETS = [^;]*;',
               'ASSETCATALOG_COMPILER_INCLUDE_ALL_APPICON_ASSETS = YES;', s)
    pbx.write_text(s)


def android():
    res = APP / "android/app/src/main/res"
    for f in res.glob("*/ic_launcher_[a-z]*.*"):
        if f.stem not in ("ic_launcher_foreground", "ic_launcher_background"):
            f.unlink()
    for key in ALTERNATES:
        im = img(key)
        for name, k in DENSITIES.items():
            im.resize((round(48 * k),) * 2, Image.LANCZOS).save(res / f"mipmap-{name}/ic_launcher_{key}.png")
            (res / f"drawable-{name}").mkdir(exist_ok=True)
            im.resize((round(108 * k),) * 2, Image.LANCZOS).save(res / f"drawable-{name}/ic_launcher_fg_{key}.png")
        (res / f"mipmap-anydpi-v26/ic_launcher_{key}.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '  <background android:drawable="@color/ic_launcher_background"/>\n'
            f'  <foreground android:drawable="@drawable/ic_launcher_fg_{key}"/>\n</adaptive-icon>\n')
    man = APP / "android/app/src/main/AndroidManifest.xml"
    s = man.read_text()
    s = re.sub(r"\n        <!-- app icons \(tools/app_icons.py\) -->.*?<!-- /app icons -->", "", s, flags=re.S)
    aliases = "".join(
        f'\n        <activity-alias android:name=".Icon_{k}" android:targetActivity=".MainActivity"'
        f' android:icon="@mipmap/{"ic_launcher" if k == MAIN else "ic_launcher_" + k}"'
        f' android:enabled="{"true" if k == MAIN else "false"}" android:exported="true">'
        '\n            <intent-filter><action android:name="android.intent.action.MAIN"/>'
        '<category android:name="android.intent.category.LAUNCHER"/></intent-filter>\n        </activity-alias>'
        for k in [MAIN] + [a for a in ALTERNATES if a in PICKER])
    s = s.replace("\n        <!-- Don't delete the meta-data below.",
                  f"\n        <!-- app icons (tools/app_icons.py) -->{aliases}\n        <!-- /app icons -->"
                  "\n        <!-- Don't delete the meta-data below.", 1)
    man.write_text(s)


def flutter_and_play():
    thumbs = APP / "assets/icon/thumbs"
    shutil.rmtree(thumbs, ignore_errors=True)
    thumbs.mkdir()
    for key in PICKER:
        img(key).resize((192, 192), Image.LANCZOS).save(thumbs / f"{key}.png")
    for f in (ROOT / "store").glob("play-icon-512-*.png"):
        f.unlink()
    for key in AB:
        img(key).resize((512, 512), Image.LANCZOS).save(ROOT / f"store/play-icon-512-{key}.png")
    (APP / "lib/settings/app_icons.g.dart").write_text(
        "// Generated by tools/app_icons.py. Do not edit.\n\n"
        "/// Icons the reader can pick in Nastavení; the first one is the default (main) icon.\n"
        f"const kAppIcons = <String>[{', '.join(repr(k) for k in PICKER)}];\n")


if __name__ == "__main__":
    main_icon()
    ios()
    android()
    flutter_and_play()
    print("main", MAIN, "| alternates", len(ALTERNATES), "| picker", len(PICKER))
