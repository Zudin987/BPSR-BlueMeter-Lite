package com.bluemeter.bluemeter_mobile

import android.content.Intent
import android.net.VpnService
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    companion object {
        private const val CHANNEL = "com.bluemeter.mobile/vpn"
        private const val EVENT_CHANNEL = "com.bluemeter.mobile/packet_stream"
        private const val UPSTREAM_EVENT_CHANNEL = "com.bluemeter.mobile/upstream_stream"
    }

    private val supportedGamePackages = listOf(
        "sea.haoplay.game.gp.bpsr",
        "com.bpsr.apj",
        "tw.haoplay.game.gp.xhgm",
        "asia.xdg.game.gp.bpsr"
    )

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            CHANNEL
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "getInstalledSupportedPackages" -> {
                    val installedPackages = supportedGamePackages.filter { gamePackage ->
                        try {
                            packageManager.getApplicationInfo(gamePackage, 0)
                            true
                        } catch (_: Exception) {
                            false
                        }
                    }
                    result.success(installedPackages)
                }

                "startVpn" -> {
                    val prepareIntent = VpnService.prepare(this)
                    if (prepareIntent != null) {
                        startActivityForResult(prepareIntent, 0)
                    } else {
                        onActivityResult(0, RESULT_OK, null)
                    }
                    result.success(null)
                }

                "stopVpn" -> {
                    val intent = Intent(this, PacketCaptureService::class.java).apply {
                        action = "STOP"
                    }
                    startService(intent)
                    result.success(null)
                }

                else -> result.notImplemented()
            }
        }

        EventChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            EVENT_CHANNEL
        ).setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                if (events == null) return
                PacketEventBus.gameSink = { data ->
                    runOnUiThread {
                        events.success(data)
                    }
                }
            }

            override fun onCancel(arguments: Any?) {
                PacketEventBus.gameSink = null
            }
        })

        EventChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            UPSTREAM_EVENT_CHANNEL
        ).setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                if (events == null) return
                PacketEventBus.upstreamSink = { data ->
                    runOnUiThread {
                        events.success(data)
                    }
                }
            }

            override fun onCancel(arguments: Any?) {
                PacketEventBus.upstreamSink = null
            }
        })
    }

    @Deprecated("Deprecated in Android, retained for the VPN permission result callback")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode == 0 && resultCode == RESULT_OK) {
            startService(Intent(this, PacketCaptureService::class.java))
        }
        super.onActivityResult(requestCode, resultCode, data)
    }

    override fun onDestroy() {
        PacketEventBus.clear()
        super.onDestroy()
    }
}
