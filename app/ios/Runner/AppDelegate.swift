import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    // The icon picker (Nastavení): alternate icons AppIcon-<key> (tools/app_icons.py); keys[0] is the main icon.
    guard let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "ToonforkAppIcon") else { return }
    let channel = FlutterMethodChannel(name: "toonfork/app_icon", binaryMessenger: registrar.messenger())
    channel.setMethodCallHandler { call, result in
      let args = call.arguments as? [String: Any]
      let keys = args?["keys"] as? [String] ?? []
      switch call.method {
      case "get":
        let name = UIApplication.shared.alternateIconName
        result(name.map { String($0.dropFirst("AppIcon-".count)) } ?? keys.first)
      case "set":
        guard let key = args?["key"] as? String, keys.contains(key) else {
          result(FlutterError(code: "bad_key", message: "unknown icon", details: nil)); return
        }
        guard UIApplication.shared.supportsAlternateIcons else { result(false); return }
        let name: String? = key == keys.first ? nil : "AppIcon-\(key)"
        UIApplication.shared.setAlternateIconName(name) { error in
          result(error == nil)
        }
      default:
        result(FlutterMethodNotImplemented)
      }
    }
  }
}
