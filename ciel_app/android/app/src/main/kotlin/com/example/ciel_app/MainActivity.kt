package com.example.ciel_app

import android.content.Intent
import android.content.pm.ResolveInfo
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterFragmentActivity() {
    private val channelName = "ciel/launcher"

    // Merk: vi viser IKKJE Ciel over den sikre låsskjermen lenger. Android lèt deg
    // ikkje opne appar over låsen, så showWhenLocked gav ein forvirrande "halvlåst"
    // tilstand (låsskjermen spratt fram når du opna ein app). Ciel er heimskjermen
    // ETTER du har låst opp normalt (fingeravtrykk/fjes = den ekte, sikre vakta).

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "launchApp" -> result.success(launchAppByName(call.argument<String>("query") ?: ""))
                    "listApps" -> result.success(listAppLabels())
                    "setLockWallpaper" -> result.success(setLockWallpaper(call.argument<ByteArray>("bytes")))
                    "openLiveWallpaper" -> { openLiveWallpaper(); result.success(true) }
                    else -> result.notImplemented()
                }
            }
    }

    /** Opnar system-førehandsvisninga for å setje det levande Ciel-bakgrunnet. */
    private fun openLiveWallpaper() {
        try {
            val intent = Intent(android.app.WallpaperManager.ACTION_CHANGE_LIVE_WALLPAPER).apply {
                putExtra(
                    android.app.WallpaperManager.EXTRA_LIVE_WALLPAPER_COMPONENT,
                    android.content.ComponentName(this@MainActivity, CielWallpaperService::class.java)
                )
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(intent)
        } catch (e: Exception) {
            try {
                startActivity(
                    Intent(android.app.WallpaperManager.ACTION_LIVE_WALLPAPER_CHOOSER)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                )
            } catch (e2: Exception) {}
        }
    }

    /** Set PNG-bytes som bakgrunn på BÅDE heim og lås (stille). Samsung-UI ligg oppå. */
    private fun setLockWallpaper(bytes: ByteArray?): Boolean {
        if (bytes == null) return false
        return try {
            val bmp = android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return false
            val wm = android.app.WallpaperManager.getInstance(this)
            wm.setBitmap(
                bmp, null, true,
                android.app.WallpaperManager.FLAG_SYSTEM or android.app.WallpaperManager.FLAG_LOCK
            )
            true
        } catch (e: Exception) {
            false
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

    // Normaliser: berre små bokstavar + tal (fjern mellomrom/teikn) — toler
    // handskrift som "good notes" vs "GoodNotes".
    private fun norm(s: String): String = s.lowercase().replace(Regex("[^a-z0-9]"), "")

    /** Finn beste app som matchar [query] på namn/pakke og opnar han. Returnerer etiketten. */
    private fun launchAppByName(query: String): String? {
        val q = norm(query)
        if (q.length < 2) return null
        val pm = packageManager
        var best: ResolveInfo? = null
        var bestScore = -1
        for (ri in launchableApps()) {
            val label = norm(ri.loadLabel(pm).toString())
            val pkg = norm(ri.activityInfo.packageName)
            val score = when {
                label == q -> 100
                label.startsWith(q) -> 85
                q.startsWith(label) && label.length >= 4 -> 78
                label.contains(q) -> 65
                pkg.contains(q) -> 50
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
