package com.example.ciel_app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.RadialGradient
import android.graphics.Shader
import android.os.Handler
import android.os.Looper
import android.service.wallpaper.WallpaperService
import android.view.SurfaceHolder
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

/**
 * Levande Ciel-bakgrunn: partiklar orbiterer kjernen som eit solsystem.
 * Fargar = trans-flagg (girl mode) eller gull, lese frå Flutter-prefs.
 * Under swipe/overgang (onZoomChanged) trekkjer partiklane seg inn til den
 * tette Ciel-bobla — "tilbake til normal Ciel".
 */
class CielWallpaperService : WallpaperService() {
    override fun onCreateEngine(): Engine = CielEngine()

    inner class CielEngine : WallpaperService.Engine() {
        private val handler = Handler(Looper.getMainLooper())
        @Volatile private var visible = false
        @Volatile private var targetMorph = 0f
        private var morph = 0f
        private var t = 0f
        private var w = 0f
        private var h = 0f

        private val blue = intArrayOf(123, 205, 255)
        private val white = intArrayOf(255, 255, 255)
        private val pink = intArrayOf(245, 169, 196)
        private val gold = intArrayOf(255, 200, 80)
        private val twoPi = (PI * 2).toFloat()

        private val n = 200
        private val ang = FloatArray(n)
        private val rad = FloatArray(n)
        private val spd = FloatArray(n)
        private val sz = FloatArray(n)
        private val band = IntArray(n)
        private val opBase = FloatArray(n)
        private val opFreq = FloatArray(n)
        private val opPhase = FloatArray(n)
        private val paint = Paint(Paint.ANTI_ALIAS_FLAG)

        init {
            val r = Random(42)
            for (i in 0 until n) {
                ang[i] = r.nextFloat() * twoPi
                rad[i] = 0.30f + r.nextFloat() * 0.62f
                spd[i] = 0.05f + r.nextFloat() * 0.22f   // alle same veg = solsystem-sirkulering
                sz[i] = 1.8f + r.nextFloat() * 3.6f
                band[i] = i % 3
                opBase[i] = 0.42f + r.nextFloat() * 0.50f
                opFreq[i] = 0.3f + r.nextFloat() * 1.2f
                opPhase[i] = r.nextFloat() * twoPi
            }
        }

        private val drawer = Runnable { frame() }

        override fun onVisibilityChanged(v: Boolean) {
            visible = v
            handler.removeCallbacks(drawer)
            if (v) handler.post(drawer)
        }

        override fun onSurfaceChanged(holder: SurfaceHolder, f: Int, width: Int, height: Int) {
            w = width.toFloat(); h = height.toFloat()
        }

        override fun onSurfaceDestroyed(holder: SurfaceHolder) {
            visible = false; handler.removeCallbacks(drawer)
        }

        override fun onZoomChanged(zoom: Float) {
            targetMorph = zoom.coerceIn(0f, 1f) // unlock/overgang → samle partiklane
        }

        private fun girlMode(): Boolean = try {
            getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
                .getBoolean("flutter.girl_permanent", true)
        } catch (e: Exception) { true }

        private fun bandColor(b: Int, girl: Boolean, alpha: Float): Int {
            val c = if (!girl) gold else when (b) { 0 -> blue; 1 -> white; else -> pink }
            val a = (alpha.coerceIn(0f, 1f) * 255).toInt()
            return Color.argb(a, c[0], c[1], c[2])
        }

        private fun frame() {
            if (!visible) return
            val holder = surfaceHolder
            var canvas: Canvas? = null
            try {
                canvas = holder.lockCanvas()
                if (canvas != null) render(canvas)
            } catch (e: Exception) {
                // ignorer
            } finally {
                if (canvas != null) try { holder.unlockCanvasAndPost(canvas) } catch (e: Exception) {}
            }
            t += 0.016f
            morph += (targetMorph - morph) * 0.08f
            handler.removeCallbacks(drawer)
            if (visible) handler.postDelayed(drawer, 16)
        }

        private fun render(c: Canvas) {
            c.drawColor(Color.BLACK)
            val cx = w / 2f
            val cy = h / 2f
            val maxR = Math.min(w, h) * 0.42f
            val girl = girlMode()

            // Mjuk aura for djupn
            val auraCol = if (!girl) gold else pink
            paint.style = Paint.Style.FILL
            paint.shader = RadialGradient(
                cx, cy, maxR * 1.2f,
                intArrayOf(Color.argb(40, auraCol[0], auraCol[1], auraCol[2]), Color.argb(0, 0, 0, 0)),
                floatArrayOf(0f, 1f), Shader.TileMode.CLAMP
            )
            c.drawCircle(cx, cy, maxR * 1.2f, paint)
            paint.shader = null

            for (i in 0 until n) {
                ang[i] += spd[i] * 0.016f
                val orbitR = maxR * rad[i]
                val tightR = maxR * 0.18f * rad[i]
                val rr = orbitR + (tightR - orbitR) * morph
                val px = cx + cos(ang[i]) * rr
                val py = cy + sin(ang[i]) * rr * 0.92f
                val op = opBase[i] * (0.5f + 0.5f * sin(t * opFreq[i] + opPhase[i]))
                paint.style = Paint.Style.FILL
                paint.color = bandColor(band[i], girl, op)
                c.drawCircle(px, py, sz[i], paint)
            }

            // Stråler
            val rot = t * 0.08f
            paint.style = Paint.Style.STROKE
            paint.strokeWidth = 3f
            for (i in 0 until 8) {
                val a = rot + i / 8f * twoPi
                val len = maxR * (0.72f + 0.08f * sin(t * 0.6f + i))
                val third = (((a % twoPi) + twoPi) % twoPi / (twoPi / 3)).toInt()
                val col = bandColor(third, girl, 0.45f)
                paint.shader = LinearGradient(
                    cx, cy, cx + cos(a) * len, cy + sin(a) * len,
                    intArrayOf(col, Color.argb(0, 0, 0, 0)),
                    floatArrayOf(0f, 1f), Shader.TileMode.CLAMP
                )
                c.drawLine(cx, cy, cx + cos(a) * len, cy + sin(a) * len, paint)
            }
            paint.shader = null

            // Kjerne — alltid kvit-lys
            val coreR = maxR * 0.12f
            val cc = if (!girl) gold else white
            paint.style = Paint.Style.FILL
            paint.shader = RadialGradient(
                cx, cy, coreR,
                intArrayOf(
                    Color.argb(255, 255, 255, 255),
                    Color.argb(210, cc[0], cc[1], cc[2]),
                    Color.argb(0, 0, 0, 0)
                ),
                floatArrayOf(0f, 0.35f, 1f), Shader.TileMode.CLAMP
            )
            c.drawCircle(cx, cy, coreR, paint)
            paint.shader = null
            paint.color = Color.WHITE
            c.drawCircle(cx, cy, 3.2f, paint)
        }
    }
}
