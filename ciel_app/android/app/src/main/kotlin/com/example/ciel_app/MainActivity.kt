package com.example.ciel_app

import android.content.Intent
import android.content.pm.ResolveInfo
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterFragmentActivity() {
    private val channelName = "ciel/launcher"

    override fun onCreate(savedInstanceState: android.os.Bundle?) {
        super.onCreate(savedInstanceState)
        // Vis Ciel OVER låsskjermen. (Android tillèt ikkje å erstatte sjølve den
        // sikre keyguarden — fingeravtrykk/PIN er framleis lag 1, jf. SPEC §5.)
        if (android.os.Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "launchApp" -> result.success(launchAppByName(call.argument<String>("query") ?: ""))
                    "listApps" -> result.success(listAppLabels())
                    else -> result.notImplemented()
                }
            }
    }

    private fun launchableApps(): List<ResolveInfo> {
        val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        return packageManager.queryIntentActivities(intent, 0)
    }

    private fun listAppLabels(): List<String> {
        val pm = packageManager
        return launchableApps().map { it.loadLabel(pm).toString() }.distinct().sorted()
    }

    /** Finn beste app som matchar [query] på namn/pakke og opnar han. Returnerer etiketten. */
    private fun launchAppByName(query: String): String? {
        val q = query.trim().lowercase()
        if (q.isEmpty()) return null
        val pm = packageManager
        var best: ResolveInfo? = null
        var bestScore = -1
        for (ri in launchableApps()) {
            val label = ri.loadLabel(pm).toString().lowercase()
            val pkg = ri.activityInfo.packageName.lowercase()
            val score = when {
                label == q -> 100
                label.startsWith(q) -> 80
                label.contains(q) -> 60
                pkg.contains(q) -> 40
                else -> -1
            }
            if (score > bestScore) { bestScore = score; best = ri }
        }
        val ri = best ?: return null
        if (bestScore < 0) return null
        val launch = pm.getLaunchIntentForPackage(ri.activityInfo.packageName) ?: return null
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        startActivity(launch)
        return ri.loadLabel(pm).toString()
    }
}
