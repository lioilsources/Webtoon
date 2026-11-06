#!/usr/bin/env python3
"""Store screenshots: boots a device, runs app/integration_test/screenshots_test.dart on it and
captures the screen whenever the test asks (GET /shot?lang=..&name=..).

    python3 store/screenshots/tools/shoot.py ios-6.9|ios-13|play-phone|play-tablet-10 [--langs cs,en]
            [--keep-device] [-- extra flutter args]

Writes store/screenshots/<set>/<locale>/NN_<name>.png. Needs the real starter pack in
app/assets/packs/starter.zip and store/screenshots/.staging/gamebook-sara.zip (stage_sara.py).
"""
import argparse
import http.server
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
APP = os.path.join(ROOT, 'app')
OUT = os.path.join(ROOT, 'store', 'screenshots')
STAGING = os.path.join(OUT, '.staging')
ADB = os.path.expanduser('~/Library/Android/sdk/platform-tools/adb')
EMULATOR = os.path.expanduser('~/Library/Android/sdk/emulator/emulator')

# reader language code -> store/listing folder
LOCALES = {
    'cs': 'cs', 'en': 'en-US', 'de': 'de-DE', 'it': 'it', 'fr': 'fr-FR', 'pl': 'pl',
    'pt-BR': 'pt-BR', 'ja': 'ja', 'ko': 'ko', 'vi': 'vi', 'ru': 'ru', 'uk': 'uk',
}

SETS = {
    'ios-6.9': dict(kind='ios', device='iPhone 17 Pro Max', size=(1320, 2868)),
    'ios-13': dict(kind='ios', device='iPad Pro 13-inch (M5)', size=(2064, 2752)),
    'play-phone': dict(kind='android', avd='Pixel_10', size=(1080, 2160), density=420),
    'play-tablet-10': dict(kind='android', avd='Pixel_10', size=(1600, 2560), density=320),
}


def run(*cmd, **kw):
    print('+', ' '.join(cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def ios_udid(name):
    out = subprocess.run(['xcrun', 'simctl', 'list', 'devices', 'available'],
                         capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        line = line.strip()
        if line.startswith(name + ' ('):
            return line[len(name) + 2:].split(')')[0]
    sys.exit(f'no simulator {name!r}')


def _iso_941():
    """9 Jan 2024 9:41 in the host's time zone, as the UTC string simctl wants."""
    import datetime
    t = datetime.datetime(2024, 1, 9, 9, 41).astimezone().astimezone(datetime.timezone.utc)
    return t.strftime('%Y-%m-%dT%H:%M:%S.000Z')


def setup_ios(cfg):
    udid = ios_udid(cfg['device'])
    subprocess.run(['xcrun', 'simctl', 'boot', udid])  # fails harmlessly when booted
    run('xcrun', 'simctl', 'bootstatus', udid, '-b')
    # US region, so the iPad status bar date reads "Sun Jan 9" (not the host's format)
    loc = subprocess.run(['xcrun', 'simctl', 'spawn', udid, 'defaults', 'read', '-g',
                          'AppleLocale'], capture_output=True, text=True).stdout.strip()
    if loc != 'en_US':
        run('xcrun', 'simctl', 'spawn', udid, 'defaults', 'write', '-g', 'AppleLocale', 'en_US')
        run('xcrun', 'simctl', 'shutdown', udid)
        run('xcrun', 'simctl', 'boot', udid)
        run('xcrun', 'simctl', 'bootstatus', udid, '-b')
    run('xcrun', 'simctl', 'ui', udid, 'appearance', 'light')
    run('xcrun', 'simctl', 'status_bar', udid, 'override', '--time', _iso_941(),
        '--dataNetwork', 'wifi', '--wifiMode', 'active', '--wifiBars', '3',
        '--cellularMode', 'active', '--cellularBars', '4', '--operatorName', '',
        '--batteryState', 'charged', '--batteryLevel', '100')
    # fresh app data: no catalog cache / old packs from another run
    subprocess.run(['xcrun', 'simctl', 'uninstall', udid, 'com.ol1n.webtoon'])
    return udid, lambda path: run('xcrun', 'simctl', 'io', udid, 'screenshot',
                                  '--type=png', path, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)


def adb(*a, **kw):
    # Right after boot, `adb shell` commands fail (exit 255) until system services are up: retry ~1 min.
    for attempt in range(30):
        try:
            return run(ADB, *a, **kw)
        except subprocess.CalledProcessError:
            if attempt == 29:
                raise
            time.sleep(2)


def setup_android(cfg):
    out = subprocess.run([ADB, 'devices'], capture_output=True, text=True).stdout
    serial = next((l.split()[0] for l in out.splitlines() if l.startswith('emulator-')), None)
    if serial is None:
        subprocess.Popen([EMULATOR, '-avd', cfg['avd'], '-no-snapshot-save', '-no-audio',
                          '-no-boot-anim'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        adb('wait-for-device')
        out = subprocess.run([ADB, 'devices'], capture_output=True, text=True).stdout
        serial = next(l.split()[0] for l in out.splitlines() if l.startswith('emulator-'))
    while subprocess.run([ADB, '-s', serial, 'shell', 'getprop', 'sys.boot_completed'],
                         capture_output=True, text=True).stdout.strip() != '1':
        time.sleep(2)
    w, h = cfg['size']
    # boot_completed comes before the window manager answers: retry `wm` for up to a minute
    for _ in range(30):
        if subprocess.run([ADB, '-s', serial, 'shell', 'wm', 'size', f'{w}x{h}']).returncode == 0:
            break
        time.sleep(2)
    else:
        raise SystemExit(f'{serial}: wm size never succeeded')
    adb('-s', serial, 'shell', 'wm', 'density', str(cfg['density']))
    adb('-s', serial, 'shell', 'cmd', 'uimode', 'night', 'no')
    # Notifications (Play Store, Safety Center, tutorials) would sit in the status bar: snooze them.
    keys = subprocess.run([ADB, '-s', serial, 'shell', 'cmd', 'notification', 'list'],
                          capture_output=True, text=True).stdout.split()
    for k in keys:
        subprocess.run([ADB, '-s', serial, 'shell', '-n', 'cmd', 'notification', 'snooze',
                        '--for', '86400000', f"'{k}'"], stdout=subprocess.DEVNULL)
    # demo mode: 9:41, full battery, no other icons. (Demo `network` commands are left out on
    # purpose: on this Android 17 image they draw every network/satellite icon twice.)
    adb('-s', serial, 'shell', 'settings', 'put', 'global', 'sysui_demo_allowed', '1')
    adb('-s', serial, 'shell', 'am', 'broadcast', '-a', 'com.android.systemui.demo', '-e',
        'command', 'exit', stdout=subprocess.DEVNULL)
    for extra in (['-e', 'command', 'enter'],
                  ['-e', 'command', 'clock', '-e', 'hhmm', '0941'],
                  ['-e', 'command', 'battery', '-e', 'level', '100', '-e', 'plugged', 'false'],
                  ['-e', 'command', 'notifications', '-e', 'visible', 'false']):
        adb('-s', serial, 'shell', 'am', 'broadcast', '-a', 'com.android.systemui.demo', *extra,
            stdout=subprocess.DEVNULL)
    subprocess.run([ADB, '-s', serial, 'uninstall', 'com.ol1n.webtoon'])

    def cap(path):
        with open(path, 'wb') as f:
            subprocess.run([ADB, '-s', serial, 'exec-out', 'screencap', '-p'], stdout=f, check=True)
    return serial, cap


def android_clean(im, density):
    """This Android 17 emulator image always shows a satellite-connectivity icon next to the
    battery in demo mode (it cannot be hidden by demo commands or icon_blacklist). It is
    system chrome, not app UI: paint every status-bar icon right of centre except the
    battery (the rightmost one) with the status bar's plain background."""
    from PIL import ImageDraw
    im = im.convert('RGB')
    w = im.width
    bg = im.getpixel((w // 2, 4))
    # the band = the status bar icon row, measured on the battery (the rightmost icon)
    probe = int(60 * density / 160)
    rows = [y for y in range(probe) if any(
        sum(abs(a - b) for a, b in zip(im.getpixel((x, y)), bg)) > 60
        for x in range(w - int(40 * density / 160), w, 2))]
    if not rows:
        return im
    band = rows[-1] + (rows[-1] - rows[0]) // 2 + 2
    if any(abs(a - b) > 6 for x in range(w // 2 - 40, w // 2 + 40, 8)
           for a, b in zip(im.getpixel((x, band // 2)), bg)):
        print('  android_clean: status bar not plain - left as is', flush=True)
        return im
    def ink(x):
        return any(sum(abs(a - b) for a, b in zip(im.getpixel((x, y)), bg)) > 60
                   for y in range(2, band))
    runs, start = [], None
    for x in range(w // 2, w):
        if ink(x):
            start = x if start is None else start
        elif start is not None:
            if runs and start - runs[-1][1] < 6:
                runs[-1] = (runs[-1][0], x)
            else:
                runs.append((start, x))
            start = None
    for x0, x1 in runs[:-1]:  # the last one is the battery
        ImageDraw.Draw(im).rectangle((x0 - 3, 0, x1 + 3, band), fill=bg)
    return im


def ipad_clean(im):
    """iPadOS 26+ runs every app in a window (no full-screen setting reachable from simctl):
    the status bar then names the app ("Toonfork" after the date) and the bottom-right corner
    has a resize grip. Both are system chrome, not app UI; paint them over with the plain
    background next to them, and only where that background is uniform."""
    im = im.convert('RGB')
    w, h = im.size
    from PIL import ImageDraw, ImageStat

    def fill(box, sample):
        x0, y0, x1, y1 = box
        ring = [im.crop((x0 - 8, y0, x0 - 2, y1)), im.crop((x0, y1 + 2, x1, y1 + 6))
                if y1 + 6 <= h else im.crop((x0, y0 - 6, x1, y0 - 2))]
        if max(max(ImageStat.Stat(r).stddev) for r in ring) > 4:
            print('  ipad_clean: background not plain at', box, '- left as is', flush=True)
            return
        ImageDraw.Draw(im).rectangle(box, fill=im.getpixel(sample))

    fill((320, 12, 460, 52), (310, 30))           # "Toonfork" after "9:41 AM  Sun Jan 9"
    fill((w - 62, h - 62, w - 4, h - 4), (w - 70, h - 30))  # window resize grip
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('set', choices=SETS)
    ap.add_argument('--langs', default=','.join(LOCALES))
    ap.add_argument('--port', type=int, default=8777)
    ap.add_argument('--keep-device', action='store_true')
    ap.add_argument('extra', nargs='*')
    a = ap.parse_args()
    cfg = SETS[a.set]
    if not os.path.exists(os.path.join(STAGING, 'gamebook-sara.zip')):
        sys.exit('run store/screenshots/tools/stage_sara.py first')
    if os.path.getsize(os.path.join(APP, 'assets/packs/starter.zip')) < 1_000_000:
        sys.exit('app/assets/packs/starter.zip is the placeholder: gh release download starter-v1 …')

    device, capture = (setup_ios if cfg['kind'] == 'ios' else setup_android)(cfg)
    host = '127.0.0.1' if cfg['kind'] == 'ios' else '10.0.2.2'
    from PIL import Image

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kw):
            super().__init__(*args, directory=STAGING, **kw)

        def log_message(self, *args):
            pass

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path != '/shot':
                return super().do_GET()
            q = urllib.parse.parse_qs(u.query)
            lang, name = q['lang'][0], q['name'][0]
            folder = os.path.join(OUT, a.set, LOCALES[lang])
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, name + '.png')
            for attempt in range(8):
                capture(path)
                im = Image.open(path)
                # The simulator sometimes draws the Dynamic Island as a black pill (an
                # active-activity state); wait for it to go away.
                if a.set != 'ios-6.9' or im.convert('RGB').getpixel((im.width // 2, 70)) != (0, 0, 0):
                    break
                print('dynamic island visible, retrying', flush=True)
                time.sleep(1.5)
            if a.set == 'ios-13':
                im = ipad_clean(im)
                im.save(path)
            elif cfg['kind'] == 'android':
                im = android_clean(im, cfg['density'])
                im.save(path)
            elif im.mode != 'RGB':  # App Store refuses alpha
                im.convert('RGB').save(path)
            msg = f'{a.set}/{LOCALES[lang]}/{name}.png {im.size}'
            ok = tuple(im.size) == tuple(cfg['size'])
            print('captured', msg, '' if ok else f'!! expected {cfg["size"]}', flush=True)
            self.send_response(200 if ok else 500)
            self.end_headers()
            self.wfile.write(msg.encode())

    srv = http.server.ThreadingHTTPServer(('0.0.0.0', a.port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        run('flutter', 'test', 'integration_test/screenshots_test.dart', '-d', device,
            '--dart-define=WEBTOON_FAKE_IAP=true',
            f'--dart-define=SHOT_HOST=http://{host}:{a.port}',
            f'--dart-define=SHOT_LANGS={a.langs}', *a.extra, cwd=APP)
    finally:
        srv.shutdown()
        if not a.keep_device:
            if cfg['kind'] == 'ios':
                subprocess.run(['xcrun', 'simctl', 'status_bar', device, 'clear'])
                subprocess.run(['xcrun', 'simctl', 'shutdown', device])
            else:
                subprocess.run([ADB, '-s', device, 'shell', 'wm', 'size', 'reset'])
                subprocess.run([ADB, '-s', device, 'shell', 'wm', 'density', 'reset'])
                subprocess.run([ADB, '-s', device, 'emu', 'kill'])


if __name__ == '__main__':
    main()
