package com.bluemeter.bluemeter_mobile

import android.content.Intent
import android.net.VpnService
import android.os.ParcelFileDescriptor
import android.util.Log
import java.io.ByteArrayOutputStream
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.net.InetSocketAddress
import java.nio.ByteBuffer
import java.nio.channels.DatagramChannel
import java.nio.channels.SelectionKey
import java.nio.channels.Selector
import java.nio.channels.SocketChannel
import java.util.ArrayDeque
import java.util.HashMap
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

class PacketCaptureService : VpnService() {
    companion object {
        private const val TAG = "BlueMeterLite"
        private const val TUN_READ_SIZE = 32767
        private const val INPUT_QUEUE_CAPACITY = 256
        private const val BUFFER_POOL_LIMIT = 64
        private const val PACKET_POOL_LIMIT = 64
        private const val MAX_POOLED_BUFFER_SIZE = 65536
        private const val BRIDGE_FLUSH_BYTES = 200 * 1024
        private const val BRIDGE_FLUSH_DELAY_MS = 1000L
        private const val SELECT_IDLE_TIMEOUT_MS = 5000L
        private const val UDP_IDLE_TIMEOUT_NANOS = 60_000_000_000L
        private const val UDP_CLEANUP_INTERVAL_NANOS = 30_000_000_000L
        private const val MAX_UDP_PENDING_BYTES = 256 * 1024
    }

    private var mInterface: ParcelFileDescriptor? = null
    private val executor: ExecutorService = Executors.newSingleThreadExecutor()
    private val flushExecutor: ScheduledExecutorService =
        Executors.newSingleThreadScheduledExecutor()
    private var flushTask: java.util.concurrent.ScheduledFuture<*>? = null

    @Volatile
    private var isRunning = false

    @Volatile
    private var networkSelector: Selector? = null

    private lateinit var tcpProxy: TcpProxy

    // The TUN reader is the only cross-thread packet producer. A bounded
    // blocking queue provides backpressure instead of dropping game packets.
    private val inputQueue = ArrayBlockingQueue<ByteBuffer>(INPUT_QUEUE_CAPACITY)
    private val outputQueue: java.util.Queue<ByteBuffer> = ArrayDeque()

    private val bufferPool = ConcurrentLinkedQueue<ByteBuffer>()
    private val bufferPoolSize = AtomicInteger(0)
    private val packetPool: ArrayDeque<Packet> = ArrayDeque()

    private fun obtainBuffer(size: Int): ByteBuffer {
        while (true) {
            val buffer = bufferPool.poll() ?: break
            bufferPoolSize.decrementAndGet()
            if (buffer.capacity() >= size) {
                buffer.clear()
                return buffer
            }
        }
        return ByteBuffer.allocate(maxOf(size, 4096))
    }

    private fun recycleBuffer(buffer: ByteBuffer) {
        if (buffer.capacity() > MAX_POOLED_BUFFER_SIZE) return

        while (true) {
            val current = bufferPoolSize.get()
            if (current >= BUFFER_POOL_LIMIT) return
            if (bufferPoolSize.compareAndSet(current, current + 1)) {
                buffer.clear()
                bufferPool.offer(buffer)
                return
            }
        }
    }

    private fun obtainPacket(): Packet {
        return if (packetPool.isEmpty()) Packet() else packetPool.removeFirst()
    }

    private fun recyclePacket(packet: Packet) {
        packet.backingBuffer = null
        if (packetPool.size < PACKET_POOL_LIMIT) {
            packetPool.addLast(packet)
        }
    }

    private val dataBuffer = ByteArrayOutputStream()
    private val upstreamBuffer = ByteArrayOutputStream()
    private val bufferLock = Any()

    @Volatile
    private var activeGameSession: String? = null

    private val gameSessionCandidates = ConcurrentHashMap.newKeySet<String>()
    private val validGameSessions = ConcurrentHashMap.newKeySet<String>()
    private val gameHandshake = byteArrayOf(0x00, 0x00, 0x00, 0x06, 0x00, 0x04)
    private val serverSignature = byteArrayOf(0x00, 0x63, 0x33, 0x53, 0x42, 0x00)

    @Volatile
    private var port5003Session: String? = null

    data class UdpKey(
        val sourceIp: Int,
        val sourcePort: Int,
        val destIp: Int,
        val destPort: Int
    )

    data class UdpSession(
        val key: UdpKey,
        val channel: DatagramChannel,
        var lastActivityNanos: Long,
        val pendingWrites: ArrayDeque<ByteBuffer> = ArrayDeque(),
        var pendingBytes: Int = 0
    )

    private val udpSessions = HashMap<UdpKey, UdpSession>()
    private val udpReadBuffer = ByteBuffer.allocate(TUN_READ_SIZE)

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "STOP") {
            stopCapture()
            stopSelf()
            return START_NOT_STICKY
        }

        startCapture()
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        stopCapture()
        executor.shutdownNow()
        flushExecutor.shutdownNow()
        PacketEventBus.clear()
        super.onDestroy()
    }

    private fun startCapture() {
        if (isRunning) return

        val builder = Builder()
            .setSession("BlueMeter Lite")
            .addAddress("10.0.0.2", 24)
            .addRoute("0.0.0.0", 0)
            .setMtu(1500)

        val supportedGamePackages = listOf(
            "sea.haoplay.game.gp.bpsr",
            "com.bpsr.apj",
            "tw.haoplay.game.gp.xhgm",
            "asia.xdg.game.gp.bpsr"
        )

        var allowedPackageCount = 0
        for (gamePackage in supportedGamePackages) {
            try {
                builder.addAllowedApplication(gamePackage)
                allowedPackageCount++
                Log.i(TAG, "Capturing package: $gamePackage")
            } catch (_: Exception) {
                // Package is not installed.
            }
        }

        if (allowedPackageCount == 0) {
            Log.e(TAG, "No supported BPSR package is installed")
            stopSelf()
            return
        }

        try {
            val selector = Selector.open()
            networkSelector = selector
            tcpProxy = TcpProxy(this, selector, ::obtainBuffer, ::handleProxyData)

            mInterface = builder.establish()
            if (mInterface == null) {
                selector.close()
                networkSelector = null
                stopSelf()
                return
            }

            isRunning = true
            executor.submit { runCaptureLoop() }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to establish VPN", e)
            isRunning = false
            try {
                networkSelector?.close()
            } catch (_: Exception) {
            }
            networkSelector = null
            stopSelf()
        }
    }

    private fun stopCapture() {
        if (!isRunning && mInterface == null) return

        isRunning = false
        synchronized(bufferLock) {
            flushTask?.cancel(false)
            flushTask = null
        }

        try {
            mInterface?.close()
        } catch (e: Exception) {
            Log.w(TAG, "Error closing VPN interface: ${e.message}")
        }
        mInterface = null

        try {
            networkSelector?.wakeup()
        } catch (_: Exception) {
        }

        // Flush a final already-decoded batch. The copy/event dispatch happens
        // outside bufferLock so the network thread is never held by Flutter.
        flushData()
    }

    private fun handleProxyData(source: String, data: ByteArray) {
        if (source.startsWith("CLOSE:")) {
            val closedSession = source.removePrefix("CLOSE:")
            if (closedSession == activeGameSession) {
                activeGameSession = null
            }
            if (closedSession == port5003Session) {
                port5003Session = null
            }
            gameSessionCandidates.remove(closedSession)
            validGameSessions.remove(closedSession)
            return
        }

        if (source.startsWith("UP:")) {
            val sessionKey = source.removePrefix("UP:")
            if (
                !gameSessionCandidates.contains(sessionKey) &&
                activeGameSession != sessionKey &&
                !validGameSessions.contains(sessionKey) &&
                !sessionKey.contains("destPort=5003") &&
                !sessionKey.contains("destPort=443") &&
                startsWithHandshake(data)
            ) {
                gameSessionCandidates.add(sessionKey)
                if (activeGameSession == null) {
                    synchronized(bufferLock) {
                        dataBuffer.reset()
                    }
                }
            }
            return
        }

        if (source.contains("destPort=443")) return

        if (source == activeGameSession) {
            appendGameData(data)
            return
        }

        if (source.contains("destPort=5003")) {
            appendUpstreamData(source, data)
            return
        }

        if (gameSessionCandidates.contains(source)) {
            if (indexOf(data, serverSignature) != -1) {
                validGameSessions.add(source)
                activeGameSession = source
                gameSessionCandidates.remove(source)
                appendGameData(data)
                return
            }

            if (activeGameSession == null) {
                appendGameData(data)
            }
            return
        }

        if (validGameSessions.contains(source)) return

        if (startsWithHandshake(data)) {
            gameSessionCandidates.add(source)
            if (activeGameSession == null) {
                synchronized(bufferLock) {
                    dataBuffer.reset()
                }
                appendGameData(data)
            }
        }
    }

    private fun startsWithHandshake(data: ByteArray): Boolean {
        if (data.size < gameHandshake.size) return false
        for (index in gameHandshake.indices) {
            if (data[index] != gameHandshake[index]) return false
        }
        return true
    }

    private fun appendGameData(data: ByteArray) {
        var flushNow = false
        synchronized(bufferLock) {
            dataBuffer.write(data)
            flushNow = scheduleFlushOrImmediateLocked()
        }
        if (flushNow) flushData()
    }

    private fun appendUpstreamData(source: String, data: ByteArray) {
        var flushNow = false
        synchronized(bufferLock) {
            if (source != port5003Session) {
                port5003Session = source
                upstreamBuffer.reset()
                upstreamBuffer.write(
                    byteArrayOf(
                        0xFF.toByte(),
                        0xFF.toByte(),
                        0xFF.toByte(),
                        0xFF.toByte()
                    )
                )
            }
            upstreamBuffer.write(data)
            flushNow = scheduleFlushOrImmediateLocked()
        }
        if (flushNow) flushData()
    }

    /** Caller must hold bufferLock. */
    private fun scheduleFlushOrImmediateLocked(): Boolean {
        val bufferedBytes = dataBuffer.size() + upstreamBuffer.size()
        if (bufferedBytes >= BRIDGE_FLUSH_BYTES) {
            flushTask?.cancel(false)
            flushTask = null
            return true
        }

        if (
            isRunning &&
            flushTask == null &&
            !flushExecutor.isShutdown
        ) {
            flushTask = flushExecutor.schedule(
                { flushData() },
                BRIDGE_FLUSH_DELAY_MS,
                TimeUnit.MILLISECONDS
            )
        }
        return false
    }

    private fun flushData() {
        var gameData: ByteArray? = null
        var upstreamData: ByteArray? = null

        synchronized(bufferLock) {
            flushTask = null
            if (dataBuffer.size() > 0) {
                gameData = dataBuffer.toByteArray()
                dataBuffer.reset()
            }
            if (upstreamBuffer.size() > 0) {
                upstreamData = upstreamBuffer.toByteArray()
                upstreamBuffer.reset()
            }
        }

        gameData?.let(PacketEventBus::emitGame)
        upstreamData?.let(PacketEventBus::emitUpstream)
    }

    private fun indexOf(data: ByteArray, pattern: ByteArray): Int {
        if (pattern.isEmpty()) return 0
        if (data.size < pattern.size) return -1

        for (i in 0..data.size - pattern.size) {
            var found = true
            for (j in pattern.indices) {
                if (data[i + j] != pattern[j]) {
                    found = false
                    break
                }
            }
            if (found) return i
        }
        return -1
    }

    private fun runCaptureLoop() {
        val vpnInterface = mInterface ?: return
        val selector = networkSelector ?: return
        val inputStream = FileInputStream(vpnInterface.fileDescriptor)
        val outputStream = FileOutputStream(vpnInterface.fileDescriptor)

        val readerThread = Thread({
            while (isRunning && mInterface != null) {
                val readBuffer = obtainBuffer(TUN_READ_SIZE)
                try {
                    val len = inputStream.read(
                        readBuffer.array(),
                        0,
                        readBuffer.capacity()
                    )
                    if (len <= 0) {
                        recycleBuffer(readBuffer)
                        continue
                    }

                    readBuffer.position(0)
                    readBuffer.limit(len)
                    inputQueue.put(readBuffer)
                    selector.wakeup()
                } catch (_: InterruptedException) {
                    recycleBuffer(readBuffer)
                    break
                } catch (e: Exception) {
                    recycleBuffer(readBuffer)
                    if (isRunning) {
                        Log.w(TAG, "TUN reader stopped: ${e.message}")
                    }
                    break
                }
            }
        }, "BlueMeterLite-TUN")
        readerThread.start()

        var lastUdpCleanup = System.nanoTime()

        try {
            while (isRunning && mInterface != null) {
                drainTunPackets()
                drainOutput(outputStream)

                // No fixed 1 ms wake-up. Socket readiness or the TUN reader
                // wakes this selector; the timeout exists only for low-rate
                // housekeeping such as UDP expiry.
                selector.select(SELECT_IDLE_TIMEOUT_MS)
                processSelectedKeys(selector)
                drainOutput(outputStream)

                val now = System.nanoTime()
                if (now - lastUdpCleanup >= UDP_CLEANUP_INTERVAL_NANOS) {
                    expireIdleUdpSessions(now)
                    lastUdpCleanup = now
                }
            }
        } catch (e: Exception) {
            if (isRunning) {
                Log.e(TAG, "Capture loop error", e)
            }
        } finally {
            readerThread.interrupt()
            try {
                readerThread.join(1000)
            } catch (_: InterruptedException) {
            }

            while (true) {
                val leftover = inputQueue.poll() ?: break
                recycleBuffer(leftover)
            }

            try {
                tcpProxy.closeAll()
            } catch (_: Exception) {
            }
            closeUdpSessions()

            try {
                selector.close()
            } catch (_: Exception) {
            }
            networkSelector = null
        }
    }

    private fun drainTunPackets() {
        var processed = 0
        while (processed < INPUT_QUEUE_CAPACITY) {
            val packetData = inputQueue.poll() ?: break
            val packet = obtainPacket()
            try {
                packet.set(packetData)
                if (packet.ipVersion == 4) {
                    when (packet.protocol) {
                        6 -> tcpProxy.processPacket(packet, outputQueue)
                        17 -> processUdpPacket(packet)
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Ignoring malformed TUN packet: ${e.message}")
            } finally {
                recyclePacket(packet)
                recycleBuffer(packetData)
            }
            processed++
        }
    }

    private fun processSelectedKeys(selector: Selector) {
        val iterator = selector.selectedKeys().iterator()
        while (iterator.hasNext()) {
            val key = iterator.next()
            iterator.remove()
            if (!key.isValid) continue

            when (key.channel()) {
                is SocketChannel -> tcpProxy.handleSelectedKey(key, outputQueue)
                is DatagramChannel -> handleUdpSelectedKey(key)
            }
        }
    }

    private fun processUdpPacket(packet: Packet) {
        val key = UdpKey(
            packet.sourceIpInt,
            packet.sourcePort,
            packet.destIpInt,
            packet.destPort
        )
        val selector = networkSelector ?: return
        var session = udpSessions[key]

        if (session == null) {
            try {
                val channel = DatagramChannel.open()
                channel.configureBlocking(false)
                protect(channel.socket())
                channel.connect(
                    InetSocketAddress(
                        ipToString(packet.destIpInt),
                        packet.destPort
                    )
                )
                session = UdpSession(key, channel, System.nanoTime())
                udpSessions[key] = session
                channel.register(selector, SelectionKey.OP_READ, session)
            } catch (e: IOException) {
                Log.w(TAG, "UDP connect failed: ${e.message}")
                return
            }
        }

        val backingBuffer = packet.backingBuffer ?: return
        try {
            val start = packet.ipHeaderLength + 8
            if (start > backingBuffer.limit()) return
            val payload = backingBuffer.duplicate().apply {
                position(start)
                limit(backingBuffer.limit())
            }.slice()

            session.lastActivityNanos = System.nanoTime()
            val written = session.channel.write(payload)
            if (written == 0 && payload.hasRemaining()) {
                val pending = ByteArray(payload.remaining())
                payload.get(pending)
                if (session.pendingBytes + pending.size > MAX_UDP_PENDING_BYTES) {
                    closeUdpSession(key, session)
                    return
                }
                session.pendingWrites.addLast(ByteBuffer.wrap(pending))
                session.pendingBytes += pending.size
                val selectionKey = session.channel.keyFor(selector)
                if (selectionKey != null && selectionKey.isValid) {
                    selectionKey.interestOps(
                        selectionKey.interestOps() or SelectionKey.OP_WRITE
                    )
                }
            }
        } catch (e: IOException) {
            closeUdpSession(key, session)
        }
    }

    private fun handleUdpSelectedKey(selectionKey: SelectionKey) {
        val session = selectionKey.attachment() as? UdpSession ?: return
        if (!selectionKey.isValid) return

        try {
            if (selectionKey.isWritable) {
                drainUdpWrites(selectionKey, session)
            }

            if (selectionKey.isValid && selectionKey.isReadable) {
                udpReadBuffer.clear()
                val read = session.channel.read(udpReadBuffer)
                if (read > 0) {
                    session.lastActivityNanos = System.nanoTime()
                    udpReadBuffer.flip()
                    enqueueUdpResponse(session, udpReadBuffer, read)
                }
            }
        } catch (_: IOException) {
            closeUdpSession(session.key, session)
        }
    }

    private fun drainUdpWrites(selectionKey: SelectionKey, session: UdpSession) {
        while (session.pendingWrites.isNotEmpty()) {
            val pending = session.pendingWrites.peekFirst()
            val written = session.channel.write(pending)
            if (written <= 0) break
            session.pendingBytes -= written
            if (pending.hasRemaining()) break
            session.pendingWrites.removeFirst()
            session.lastActivityNanos = System.nanoTime()
        }

        if (selectionKey.isValid && session.pendingWrites.isEmpty()) {
            selectionKey.interestOps(SelectionKey.OP_READ)
        }
    }

    private fun enqueueUdpResponse(
        session: UdpSession,
        payload: ByteBuffer,
        dataSize: Int
    ) {
        val outBuffer = obtainBuffer(20 + 8 + dataSize)
        val key = session.key

        outBuffer.put(0, 0x45.toByte())
        outBuffer.putShort(2, (20 + 8 + dataSize).toShort())
        outBuffer.putShort(4, 0)
        outBuffer.putShort(6, 0)
        outBuffer.put(8, 64.toByte())
        outBuffer.put(9, 17.toByte())
        outBuffer.putShort(10, 0)
        outBuffer.putInt(12, key.destIp)
        outBuffer.putInt(16, key.sourceIp)

        outBuffer.putShort(20, key.destPort.toShort())
        outBuffer.putShort(22, key.sourcePort.toShort())
        outBuffer.putShort(24, (8 + dataSize).toShort())
        outBuffer.putShort(26, 0)

        outBuffer.position(28)
        outBuffer.put(payload)
        outBuffer.flip()

        var sum = 0
        for (i in 0 until 20 step 2) {
            sum += outBuffer.getShort(i).toInt() and 0xFFFF
        }
        while ((sum shr 16) > 0) {
            sum = (sum and 0xFFFF) + (sum shr 16)
        }
        outBuffer.putShort(10, sum.inv().toShort())
        outputQueue.add(outBuffer)
    }

    private fun expireIdleUdpSessions(nowNanos: Long) {
        val iterator = udpSessions.entries.iterator()
        while (iterator.hasNext()) {
            val entry = iterator.next()
            val session = entry.value
            if (
                session.pendingWrites.isEmpty() &&
                nowNanos - session.lastActivityNanos >= UDP_IDLE_TIMEOUT_NANOS
            ) {
                try {
                    session.channel.keyFor(networkSelector)?.cancel()
                } catch (_: Exception) {
                }
                try {
                    session.channel.close()
                } catch (_: Exception) {
                }
                iterator.remove()
            }
        }
    }

    private fun closeUdpSession(key: UdpKey, session: UdpSession) {
        udpSessions.remove(key)
        session.pendingWrites.clear()
        session.pendingBytes = 0
        try {
            session.channel.keyFor(networkSelector)?.cancel()
        } catch (_: Exception) {
        }
        try {
            session.channel.close()
        } catch (_: Exception) {
        }
    }

    private fun closeUdpSessions() {
        val snapshot = udpSessions.values.toList()
        udpSessions.clear()
        for (session in snapshot) {
            session.pendingWrites.clear()
            try {
                session.channel.close()
            } catch (_: Exception) {
            }
        }
    }

    private fun drainOutput(outputStream: FileOutputStream) {
        while (true) {
            val packet = outputQueue.poll() ?: break
            try {
                outputStream.write(packet.array(), 0, packet.limit())
            } finally {
                recycleBuffer(packet)
            }
        }
    }

    private fun ipToString(ip: Int): String {
        return "${(ip ushr 24) and 0xFF}.${(ip ushr 16) and 0xFF}." +
            "${(ip ushr 8) and 0xFF}.${ip and 0xFF}"
    }
}
