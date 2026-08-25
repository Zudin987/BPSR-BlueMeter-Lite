package com.bluemeter.bluemeter_mobile

/**
 * In-process bridge between the VPN service and Flutter's EventChannels.
 *
 * The upstream app used package-scoped Android broadcasts for every packet
 * batch. Lite keeps the same Flutter API but avoids the extra Intent marshal,
 * BroadcastReceiver dispatch and byte-array handoff.
 */
object PacketEventBus {
    @Volatile
    var gameSink: ((ByteArray) -> Unit)? = null

    @Volatile
    var upstreamSink: ((ByteArray) -> Unit)? = null

    fun emitGame(data: ByteArray) {
        gameSink?.invoke(data)
    }

    fun emitUpstream(data: ByteArray) {
        upstreamSink?.invoke(data)
    }

    fun clear() {
        gameSink = null
        upstreamSink = null
    }
}
