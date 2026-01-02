using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using Newtonsoft.Json;

namespace DysonMCP
{
    /// <summary>
    /// Simple WebSocket server for streaming metrics to MCP clients.
    /// Implements RFC 6455 WebSocket protocol.
    /// </summary>
    public class WebSocketServer
    {
        private readonly int _port;
        private TcpListener _listener;
        private Thread _acceptThread;
        private volatile bool _running;

        private readonly ConcurrentDictionary<int, WebSocketClient> _clients;
        private int _nextClientId;

        /// <summary>
        /// True if there are connected clients waiting for metrics.
        /// </summary>
        public bool HasClients => _clients.Count > 0;

        /// <summary>
        /// Number of connected clients.
        /// </summary>
        public int ClientCount => _clients.Count;

        public WebSocketServer(int port = 8470)
        {
            _port = port;
            _clients = new ConcurrentDictionary<int, WebSocketClient>();
        }

        /// <summary>
        /// Start the WebSocket server.
        /// </summary>
        public void Start()
        {
            if (_running) return;

            try
            {
                _listener = new TcpListener(IPAddress.Any, _port);
                _listener.Start();
                _running = true;

                _acceptThread = new Thread(AcceptLoop)
                {
                    Name = "DysonMCP-WebSocket-Accept",
                    IsBackground = true
                };
                _acceptThread.Start();

                DysonMCPPlugin.Log?.LogInfo($"WebSocket server started on port {_port}");
            }
            catch (Exception ex)
            {
                DysonMCPPlugin.Log?.LogError($"Failed to start WebSocket server: {ex.Message}");
                throw;
            }
        }

        /// <summary>
        /// Stop the WebSocket server.
        /// </summary>
        public void Stop()
        {
            _running = false;

            // Close all clients
            foreach (var client in _clients.Values)
            {
                try
                {
                    client.Close();
                }
                catch { }
            }
            _clients.Clear();

            // Stop listener
            try
            {
                _listener?.Stop();
            }
            catch { }

            // Wait for accept thread
            if (_acceptThread != null && _acceptThread.IsAlive)
            {
                _acceptThread.Join(1000);
            }

            DysonMCPPlugin.Log?.LogInfo("WebSocket server stopped");
        }

        /// <summary>
        /// Broadcast metrics to all connected clients.
        /// </summary>
        public void BroadcastMetrics(MetricsSnapshot metrics)
        {
            if (_clients.Count == 0) return;

            try
            {
                string json = JsonConvert.SerializeObject(metrics, Formatting.None);
                byte[] frame = CreateWebSocketFrame(json);

                var disconnected = new List<int>();

                foreach (var kvp in _clients)
                {
                    try
                    {
                        if (!kvp.Value.Send(frame))
                        {
                            disconnected.Add(kvp.Key);
                        }
                    }
                    catch
                    {
                        disconnected.Add(kvp.Key);
                    }
                }

                // Clean up disconnected clients
                foreach (int id in disconnected)
                {
                    if (_clients.TryRemove(id, out var client))
                    {
                        client.Close();
                    }
                }
            }
            catch (Exception ex)
            {
                if (DysonMCPPlugin.EnableDetailedLogging?.Value == true)
                {
                    DysonMCPPlugin.Log?.LogWarning($"Broadcast error: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Accept incoming connections.
        /// </summary>
        private void AcceptLoop()
        {
            while (_running)
            {
                try
                {
                    if (_listener.Pending())
                    {
                        var tcpClient = _listener.AcceptTcpClient();
                        ThreadPool.QueueUserWorkItem(_ => HandleConnection(tcpClient));
                    }
                    else
                    {
                        Thread.Sleep(100);
                    }
                }
                catch (SocketException) when (!_running)
                {
                    // Expected when stopping
                }
                catch (Exception ex)
                {
                    if (DysonMCPPlugin.EnableDetailedLogging?.Value == true)
                    {
                        DysonMCPPlugin.Log?.LogWarning($"Accept error: {ex.Message}");
                    }
                    Thread.Sleep(1000);
                }
            }
        }

        /// <summary>
        /// Handle incoming WebSocket connection.
        /// </summary>
        private void HandleConnection(TcpClient tcpClient)
        {
            try
            {
                var stream = tcpClient.GetStream();
                byte[] buffer = new byte[4096];

                // Read HTTP upgrade request
                int bytesRead = stream.Read(buffer, 0, buffer.Length);
                string request = Encoding.UTF8.GetString(buffer, 0, bytesRead);

                // Parse WebSocket key
                string wsKey = null;
                foreach (string line in request.Split(new[] { "\r\n" }, StringSplitOptions.None))
                {
                    if (line.StartsWith("Sec-WebSocket-Key:", StringComparison.OrdinalIgnoreCase))
                    {
                        wsKey = line.Substring(18).Trim();
                        break;
                    }
                }

                if (string.IsNullOrEmpty(wsKey))
                {
                    tcpClient.Close();
                    return;
                }

                // Generate accept key
                string acceptKey = GenerateAcceptKey(wsKey);

                // Send upgrade response
                string response =
                    "HTTP/1.1 101 Switching Protocols\r\n" +
                    "Upgrade: websocket\r\n" +
                    "Connection: Upgrade\r\n" +
                    $"Sec-WebSocket-Accept: {acceptKey}\r\n" +
                    "\r\n";

                byte[] responseBytes = Encoding.UTF8.GetBytes(response);
                stream.Write(responseBytes, 0, responseBytes.Length);

                // Create client and add to list
                int clientId = Interlocked.Increment(ref _nextClientId);
                var wsClient = new WebSocketClient(clientId, tcpClient, stream);
                _clients[clientId] = wsClient;

                DysonMCPPlugin.Log?.LogInfo($"WebSocket client {clientId} connected");

                // Keep connection alive
                while (_running && wsClient.IsConnected)
                {
                    Thread.Sleep(100);

                    // Handle incoming messages (ping/pong, close)
                    if (stream.DataAvailable)
                    {
                        bytesRead = stream.Read(buffer, 0, buffer.Length);
                        if (bytesRead > 0)
                        {
                            var frameType = ParseWebSocketFrame(buffer, bytesRead, out _);
                            if (frameType == WebSocketOpcode.Close)
                            {
                                break;
                            }
                            else if (frameType == WebSocketOpcode.Ping)
                            {
                                // Send pong
                                byte[] pong = CreateWebSocketFrame("", WebSocketOpcode.Pong);
                                wsClient.Send(pong);
                            }
                        }
                    }
                }

                // Remove client
                _clients.TryRemove(clientId, out _);
                wsClient.Close();
                DysonMCPPlugin.Log?.LogInfo($"WebSocket client {clientId} disconnected");
            }
            catch (Exception ex)
            {
                if (DysonMCPPlugin.EnableDetailedLogging?.Value == true)
                {
                    DysonMCPPlugin.Log?.LogWarning($"Connection error: {ex.Message}");
                }
                tcpClient.Close();
            }
        }

        /// <summary>
        /// Generate WebSocket accept key per RFC 6455.
        /// </summary>
        private static string GenerateAcceptKey(string key)
        {
            const string guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
            using (var sha1 = SHA1.Create())
            {
                byte[] hash = sha1.ComputeHash(Encoding.UTF8.GetBytes(key + guid));
                return Convert.ToBase64String(hash);
            }
        }

        /// <summary>
        /// Create a WebSocket frame for sending data.
        /// </summary>
        private static byte[] CreateWebSocketFrame(string data, WebSocketOpcode opcode = WebSocketOpcode.Text)
        {
            byte[] payload = Encoding.UTF8.GetBytes(data);
            byte[] frame;

            // Limit payload size to 1MB to prevent memory issues
            if (payload.Length > 1_000_000)
            {
                DysonMCPPlugin.Log?.LogWarning($"Payload too large ({payload.Length} bytes), truncating message");
                payload = Encoding.UTF8.GetBytes("{\"error\":\"payload_too_large\"}");
            }

            if (payload.Length <= 125)
            {
                frame = new byte[2 + payload.Length];
                frame[0] = (byte)(0x80 | (int)opcode); // FIN + opcode
                frame[1] = (byte)payload.Length;
                Array.Copy(payload, 0, frame, 2, payload.Length);
            }
            else if (payload.Length <= 65535)
            {
                frame = new byte[4 + payload.Length];
                frame[0] = (byte)(0x80 | (int)opcode);
                frame[1] = 126;
                frame[2] = (byte)(payload.Length >> 8);
                frame[3] = (byte)(payload.Length & 0xFF);
                Array.Copy(payload, 0, frame, 4, payload.Length);
            }
            else
            {
                // Use long for proper 64-bit length encoding
                long len = payload.Length;
                frame = new byte[10 + payload.Length];
                frame[0] = (byte)(0x80 | (int)opcode);
                frame[1] = 127;
                for (int i = 0; i < 8; i++)
                {
                    frame[2 + i] = (byte)(len >> ((7 - i) * 8));
                }
                Array.Copy(payload, 0, frame, 10, payload.Length);
            }

            return frame;
        }

        /// <summary>
        /// Parse incoming WebSocket frame.
        /// </summary>
        private static WebSocketOpcode ParseWebSocketFrame(byte[] data, int length, out string payload)
        {
            payload = null;
            if (length < 2) return WebSocketOpcode.Invalid;

            var opcode = (WebSocketOpcode)(data[0] & 0x0F);
            bool masked = (data[1] & 0x80) != 0;
            int payloadLength = data[1] & 0x7F;

            int offset = 2;
            if (payloadLength == 126)
            {
                payloadLength = (data[2] << 8) | data[3];
                offset = 4;
            }
            else if (payloadLength == 127)
            {
                payloadLength = 0;
                for (int i = 0; i < 8; i++)
                {
                    payloadLength = (payloadLength << 8) | data[2 + i];
                }
                offset = 10;
            }

            byte[] maskKey = null;
            if (masked)
            {
                maskKey = new byte[4];
                Array.Copy(data, offset, maskKey, 0, 4);
                offset += 4;
            }

            if (payloadLength > 0 && offset + payloadLength <= length)
            {
                byte[] payloadBytes = new byte[payloadLength];
                Array.Copy(data, offset, payloadBytes, 0, payloadLength);

                if (masked && maskKey != null)
                {
                    for (int i = 0; i < payloadBytes.Length; i++)
                    {
                        payloadBytes[i] ^= maskKey[i % 4];
                    }
                }

                payload = Encoding.UTF8.GetString(payloadBytes);
            }

            return opcode;
        }

        private enum WebSocketOpcode
        {
            Invalid = -1,
            Continuation = 0x0,
            Text = 0x1,
            Binary = 0x2,
            Close = 0x8,
            Ping = 0x9,
            Pong = 0xA
        }
    }

    /// <summary>
    /// Represents a connected WebSocket client.
    /// </summary>
    internal class WebSocketClient
    {
        public int Id { get; }
        private readonly TcpClient _tcpClient;
        private readonly NetworkStream _stream;
        private readonly object _sendLock = new object();

        public bool IsConnected => _tcpClient?.Connected ?? false;

        public WebSocketClient(int id, TcpClient tcpClient, NetworkStream stream)
        {
            Id = id;
            _tcpClient = tcpClient;
            _stream = stream;
        }

        public bool Send(byte[] data)
        {
            lock (_sendLock)
            {
                try
                {
                    if (!IsConnected) return false;
                    _stream.Write(data, 0, data.Length);
                    return true;
                }
                catch
                {
                    return false;
                }
            }
        }

        public void Close()
        {
            try
            {
                _stream?.Close();
                _tcpClient?.Close();
            }
            catch { }
        }
    }
}
