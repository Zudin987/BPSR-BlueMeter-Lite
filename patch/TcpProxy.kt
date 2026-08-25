/*
 * BlueMeter Lite TCP proxy.
 * Derived from jbourny/bluemetermobile under AGPL-3.0-or-later.
 */
package com.bluemeter.bluemeter_mobile

import android.net.VpnService
import android.util.Log
import java.io.IOException
import java.net.InetSocketAddress
import java.nio.ByteBuffer
import java.nio.channels.SelectionKey
import java.nio.channels.Selector
import java.nio.channels.SocketChannel
import java.util.ArrayDeque
import java.util.HashMap

class TcpProxy(
    private val vpnService: VpnService,
    private val selector: Selector,
    private val bufferProvider: (Int) -> ByteBuffer,
    private val onDataReceived: (String, ByteArray) -> Unit
) {
    companion object {
        private const val TAG = "BlueMeterLite"
        private const val MSS = 1400
        private const val MAX_PENDING_BYTES = 4 * 1024 * 1024
    }

    private val sessions = HashMap<SessionKey, Session>()
    private val readBuffer = ByteBuffer.allocate(65536)

    data class SessionKey(
        val sourceIp: Int,
        val sourcePort: Int,
        val destIp: Int,
        val destPort: Int
    )

    fun processPacket(packet: Packet, outputQueue: java.util.Queue<ByteBuffer>) {
        val key = SessionKey(
            packet.sourceIpInt,
            packet.sourcePort,
            packet.destIpInt,
            packet.destPort
        )
        var session = sessions[key]

        if (packet.flags and Packet.TCP_SYN != 0) {
            if (session == null) {
                session = Session(
                    packet.sourceIpInt,
                    packet.sourcePort,
                    packet.destIpInt,
                    packet.destPort
                )
                sessions[key] = session

                try {
                    val channel = SocketChannel.open()
                    channel.configureBlocking(false)
                    channel.socket().tcpNoDelay = true
                    vpnService.protect(channel.socket())

                    session.channel = channel
                    session.state = SessionState.SYN_RECEIVED
                    session.clientSeq = packet.seqNum + 1
                    session.mySeq = 1000

                    val connected = channel.connect(
                        InetSocketAddress(ipToString(packet.destIpInt), packet.destPort)
                    )
                    val ops = if (connected) {
                        SelectionKey.OP_READ
                    } else {
                        SelectionKey.OP_CONNECT
                    }

                    channel.register(selector, ops, session)

                    if (connected) {
                        session.state = SessionState.ESTABLISHED
                        sendTcpPacket(
                            session,
                            Packet.TCP_SYN or Packet.TCP_ACK,
                            null,
                            0,
                            0,
                            outputQueue
                        )
                        session.mySeq++
                    }

                    Log.i(TAG, "TCP session opened: $key")
                } catch (e: IOException) {
                    Log.e(TAG, "TCP connect failed: $key — ${e.message}")
                    closeSession(key, session, notify = true)
                }
            }
            return
        }

        if (session == null) return

        if (packet.flags and Packet.TCP_RST != 0) {
            closeSession(key, session, notify = true)
            return
        }

        if (packet.flags and Packet.TCP_FIN != 0) {
            session.state = SessionState.FIN_WAIT
            if (packet.seqNum >= session.clientSeq) {
                session.clientSeq = packet.seqNum + 1
            }
            sendTcpPacket(session, Packet.TCP_ACK, null, 0, 0, outputQueue)
            closeSession(key, session, notify = true)
            return
        }

        if (packet.flags and Packet.TCP_ACK == 0 || packet.payloadSize <= 0) {
            return
        }

        val backingBuffer = packet.backingBuffer ?: return

        // The proxy terminates the app-facing TCP stream. Do not forward an
        // out-of-order segment and never duplicate bytes from a retransmission.
        // ACKing the last contiguous byte naturally asks Android's TCP stack to
        // retransmit a missing segment.
        val overlap = when {
            packet.seqNum > session.clientSeq -> {
                sendTcpPacket(session, Packet.TCP_ACK, null, 0, 0, outputQueue)
                return
            }
            packet.seqNum < session.clientSeq -> {
                (session.clientSeq - packet.seqNum)
                    .coerceAtMost(packet.payloadSize.toLong())
                    .toInt()
            }
            else -> 0
        }

        val payloadLength = packet.payloadSize - overlap
        if (payloadLength <= 0) {
            sendTcpPacket(session, Packet.TCP_ACK, null, 0, 0, outputQueue)
            return
        }

        if (session.pendingBytes + payloadLength > MAX_PENDING_BYTES) {
            Log.w(TAG, "Closing overloaded TCP session: $key")
            sendTcpPacket(session, Packet.TCP_RST, null, 0, 0, outputQueue)
            closeSession(key, session, notify = true)
            return
        }

        val payload = ByteArray(payloadLength)
        try {
            backingBuffer.position(
                packet.ipHeaderLength + packet.tcpHeaderLength + overlap
            )
            backingBuffer.get(payload)

            // One payload allocation is retained until the non-blocking remote
            // socket accepts it. No additional per-segment copies are made.
            session.pendingWrites.addLast(ByteBuffer.wrap(payload))
            session.pendingBytes += payloadLength
            session.clientSeq += payloadLength

            sendTcpPacket(session, Packet.TCP_ACK, null, 0, 0, outputQueue)
            onDataReceived("UP:$key", payload)

            if (session.state == SessionState.ESTABLISHED) {
                enableWriteInterest(session)
            }
        } catch (e: Exception) {
            Log.w(TAG, "TCP enqueue failed: $key — ${e.message}")
            closeSession(key, session, notify = true)
        }
    }

    /** Handle one SocketChannel key selected by PacketCaptureService. */
    fun handleSelectedKey(
        selectionKey: SelectionKey,
        outputQueue: java.util.Queue<ByteBuffer>
    ) {
        if (!selectionKey.isValid) return

        val session = selectionKey.attachment() as? Session ?: return
        val sessionKey = SessionKey(
            session.sourceIp,
            session.sourcePort,
            session.destIp,
            session.destPort
        )

        try {
            val channel = selectionKey.channel() as SocketChannel

            if (selectionKey.isConnectable) {
                if (channel.finishConnect()) {
                    session.state = SessionState.ESTABLISHED
                    selectionKey.interestOps(
                        SelectionKey.OP_READ or
                            if (session.pendingWrites.isNotEmpty()) {
                                SelectionKey.OP_WRITE
                            } else {
                                0
                            }
                    )

                    sendTcpPacket(
                        session,
                        Packet.TCP_SYN or Packet.TCP_ACK,
                        null,
                        0,
                        0,
                        outputQueue
                    )
                    session.mySeq++
                }
            }

            if (selectionKey.isValid && selectionKey.isWritable) {
                drainPendingWrites(selectionKey, session)
            }

            if (selectionKey.isValid && selectionKey.isReadable) {
                readBuffer.clear()
                val read = channel.read(readBuffer)

                if (read == -1) {
                    sendTcpPacket(
                        session,
                        Packet.TCP_FIN or Packet.TCP_ACK,
                        null,
                        0,
                        0,
                        outputQueue
                    )
                    closeSession(sessionKey, session, notify = true)
                } else if (read > 0) {
                    readBuffer.flip()
                    val data = ByteArray(read)
                    readBuffer.get(data)

                    // The same server-read array is used for the analyzer bridge
                    // and every 1400-byte TUN segment. The old proxy allocated a
                    // second ByteArray for each segment via copyOfRange().
                    onDataReceived(sessionKey.toString(), data)

                    var offset = 0
                    while (offset < data.size) {
                        val chunkSize = minOf(MSS, data.size - offset)
                        val flags = if (offset + chunkSize >= data.size) {
                            Packet.TCP_ACK or Packet.TCP_PSH
                        } else {
                            Packet.TCP_ACK
                        }

                        sendTcpPacket(
                            session,
                            flags,
                            data,
                            offset,
                            chunkSize,
                            outputQueue
                        )
                        session.mySeq += chunkSize
                        offset += chunkSize
                    }
                }
            }
        } catch (e: IOException) {
            Log.w(TAG, "TCP selector failure: $sessionKey — ${e.message}")
            closeSession(sessionKey, session, notify = true)
        } catch (e: Exception) {
            Log.w(TAG, "TCP session failure: $sessionKey — ${e.message}")
            closeSession(sessionKey, session, notify = true)
        }
    }

    private fun enableWriteInterest(session: Session) {
        val channel = session.channel ?: return
        val key = channel.keyFor(selector) ?: return
        if (!key.isValid) return
        key.interestOps(
            key.interestOps() or SelectionKey.OP_WRITE or SelectionKey.OP_READ
        )
    }

    private fun drainPendingWrites(key: SelectionKey, session: Session) {
        val channel = session.channel ?: return

        while (session.pendingWrites.isNotEmpty()) {
            val buffer = session.pendingWrites.peekFirst()
            val written = channel.write(buffer)

            if (written < 0) {
                throw IOException("Remote socket closed during write")
            }
            if (written == 0) break

            session.pendingBytes -= written
            if (buffer.hasRemaining()) break
            session.pendingWrites.removeFirst()
        }

        if (key.isValid) {
            val writeFlag = if (session.pendingWrites.isNotEmpty()) {
                SelectionKey.OP_WRITE
            } else {
                0
            }
            key.interestOps(SelectionKey.OP_READ or writeFlag)
        }
    }

    fun closeAll() {
        val snapshot = sessions.entries.toList()
        for ((key, session) in snapshot) {
            closeSession(key, session, notify = false)
        }
        sessions.clear()
    }

    private fun closeSession(
        key: SessionKey,
        session: Session,
        notify: Boolean
    ) {
        sessions.remove(key)
        session.pendingWrites.clear()
        session.pendingBytes = 0

        try {
            session.channel?.keyFor(selector)?.cancel()
        } catch (_: Exception) {
        }

        try {
            session.channel?.close()
        } catch (_: Exception) {
        }

        session.channel = null
        session.state = SessionState.CLOSED

        if (notify) {
            onDataReceived("CLOSE:$key", ByteArray(0))
        }
    }

    private fun sendTcpPacket(
        session: Session,
        flags: Int,
        data: ByteArray?,
        dataOffset: Int,
        dataSize: Int,
        outputQueue: java.util.Queue<ByteBuffer>
    ) {
        val bufferSize = maxOf(2048, dataSize + 100)
        val buffer = bufferProvider(bufferSize)

        buffer.put(0, 0x45.toByte())
        buffer.putShort(2, 0)
        buffer.putShort(4, 0)
        buffer.putShort(6, 0)
        buffer.put(8, 64.toByte())
        buffer.put(9, 6.toByte())
        buffer.putShort(10, 0)

        buffer.putInt(12, session.destIp)
        buffer.putInt(16, session.sourceIp)

        val ipHeaderLen = 20
        buffer.putShort(ipHeaderLen, session.destPort.toShort())
        buffer.putShort(ipHeaderLen + 2, session.sourcePort.toShort())
        buffer.putInt(ipHeaderLen + 4, session.mySeq.toInt())
        buffer.putInt(ipHeaderLen + 8, session.clientSeq.toInt())
        buffer.put(ipHeaderLen + 12, 0x50.toByte())
        buffer.put(ipHeaderLen + 13, flags.toByte())
        buffer.putShort(ipHeaderLen + 14, 64000.toShort())
        buffer.putShort(ipHeaderLen + 16, 0)
        buffer.putShort(ipHeaderLen + 18, 0)

        if (data != null && dataSize > 0) {
            buffer.position(ipHeaderLen + 20)
            buffer.put(data, dataOffset, dataSize)
        }

        val totalLen = ipHeaderLen + 20 + dataSize
        buffer.putShort(2, totalLen.toShort())
        buffer.limit(totalLen)

        buffer.putShort(10, 0)
        var sum = 0
        for (i in 0 until 20 step 2) {
            sum += buffer.getShort(i).toInt() and 0xFFFF
        }
        while ((sum shr 16) > 0) {
            sum = (sum and 0xFFFF) + (sum shr 16)
        }
        buffer.putShort(10, sum.inv().toShort())

        sum = 0
        sum += (buffer.getInt(12) shr 16) and 0xFFFF
        sum += buffer.getInt(12) and 0xFFFF
        sum += (buffer.getInt(16) shr 16) and 0xFFFF
        sum += buffer.getInt(16) and 0xFFFF
        sum += 6
        sum += 20 + dataSize

        for (i in 0 until (20 + dataSize) step 2) {
            if (i == (20 + dataSize) - 1) {
                sum += (buffer.get(20 + i).toInt() and 0xFF) shl 8
            } else {
                sum += buffer.getShort(20 + i).toInt() and 0xFFFF
            }
        }

        while ((sum shr 16) > 0) {
            sum = (sum and 0xFFFF) + (sum shr 16)
        }

        buffer.putShort(ipHeaderLen + 16, sum.inv().toShort())
        outputQueue.add(buffer)
    }

    private fun ipToString(ip: Int): String {
        return "${(ip ushr 24) and 0xFF}.${(ip ushr 16) and 0xFF}." +
            "${(ip ushr 8) and 0xFF}.${ip and 0xFF}"
    }

    data class Session(
        val sourceIp: Int,
        val sourcePort: Int,
        val destIp: Int,
        val destPort: Int,
        var channel: SocketChannel? = null,
        var state: SessionState = SessionState.CLOSED,
        var clientSeq: Long = 0,
        var mySeq: Long = 0,
        val pendingWrites: ArrayDeque<ByteBuffer> = ArrayDeque(),
        var pendingBytes: Int = 0
    )

    enum class SessionState {
        CLOSED,
        SYN_RECEIVED,
        ESTABLISHED,
        FIN_WAIT
    }
}
