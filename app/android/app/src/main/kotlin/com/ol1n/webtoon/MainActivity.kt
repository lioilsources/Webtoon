package com.ol1n.webtoon

import android.content.ComponentName
import android.content.pm.PackageManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/** The icon picker (Nastavení): each icon is an activity-alias .Icon_<key> (tools/app_icons.py); exactly one
 *  is enabled. "get" returns the enabled key, "set" enables one and disables the others. */
class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "toonfork/app_icon").setMethodCallHandler { call, result ->
            val keys = call.argument<List<String>>("keys") ?: emptyList()
            val pm = packageManager
            fun alias(k: String) = ComponentName(packageName, "$packageName.Icon_$k")
            fun enabled(k: String): Boolean = when (pm.getComponentEnabledSetting(alias(k))) {
                PackageManager.COMPONENT_ENABLED_STATE_ENABLED -> true
                PackageManager.COMPONENT_ENABLED_STATE_DISABLED -> false
                else -> k == keys.firstOrNull() // manifest default: only the main icon is enabled
            }
            when (call.method) {
                "get" -> result.success(keys.firstOrNull { enabled(it) })
                "set" -> {
                    val key = call.argument<String>("key")
                    if (key == null || key !in keys) {
                        result.error("bad_key", "unknown icon $key", null)
                    } else {
                        // enable the new one first, so there is never a moment without a launcher entry
                        pm.setComponentEnabledSetting(alias(key), PackageManager.COMPONENT_ENABLED_STATE_ENABLED, PackageManager.DONT_KILL_APP)
                        for (k in keys) if (k != key) {
                            pm.setComponentEnabledSetting(alias(k), PackageManager.COMPONENT_ENABLED_STATE_DISABLED, PackageManager.DONT_KILL_APP)
                        }
                        result.success(true)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }
}
