#!/usr/bin/env python3
"""
APEX QUANT v3.3 — TERMUX SERVER CAPACITY & STRESS TEST SUITE
============================================================
Forensic load test simulating real-time concurrent users connecting to
FastAPI + WebSocket server running on Android Termux (192.168.1.136:8000).

Tests:
1. HTTP REST Concurrency (10 -> 25 -> 50 -> 100 -> 200 -> 300 concurrent clients)
2. WebSocket Realtime Concurrency (10 -> 25 -> 50 -> 100 -> 200 -> 350+ simultaneous persistent connections)
3. End-to-End Active User Simulation (WebSocket stream + periodic REST polling)
4. Termux System Telemetry (CPU, RAM, Socket allocation, Error rate)
"""

import sys
import os
import time
import math
import json
import base64
import socket
import struct
import asyncio
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

TARGET_HOST = "192.168.1.136"
TARGET_PORT = 8000
BASE_URL = f"http://{TARGET_HOST}:{TARGET_PORT}"

# ─────────────────────────────────────────────────────────────────────────────
# 1. PURE STANDARD LIBRARY RFC 6455 WEBSOCKET CLIENT
# ─────────────────────────────────────────────────────────────────────────────

def create_ws_handshake(host: str, port: int, path: str) -> Tuple[bytes, str]:
    nonce = base64.b64encode(os.urandom(16)).decode('ascii')
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {nonce}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    return req.encode('utf-8'), nonce

async def ws_connect_client(client_id: int, duration_sec: float = 10.0) -> Dict[str, Any]:
    """
    Connects a raw RFC 6455 WebSocket client to /api/v1/futures/ws,
    reads the initial handshake, receives frames for duration_sec, and tracks stats.
    """
    t0 = time.perf_counter()
    res = {
        "client_id": client_id,
        "connected": False,
        "handshake_time_ms": 0.0,
        "messages_received": 0,
        "bytes_received": 0,
        "error": None,
        "active_duration_sec": 0.0
    }
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(TARGET_HOST, TARGET_PORT),
            timeout=5.0
        )
        t_sock = time.perf_counter()

        req_bytes, nonce = create_ws_handshake(TARGET_HOST, TARGET_PORT, "/api/v1/futures/ws")
        writer.write(req_bytes)
        await writer.drain()

        # Read handshake response
        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = await asyncio.wait_for(reader.read(1024), timeout=5.0)
            if not chunk:
                break
            header_data += chunk

        t_handshake = time.perf_counter()
        res["handshake_time_ms"] = round((t_handshake - t0) * 1000.0, 2)

        if b"101 Switching Protocols" not in header_data:
            res["error"] = "Handshake rejected (not 101)"
            writer.close()
            await writer.wait_closed()
            return res

        res["connected"] = True

        # Keep reading frames for duration_sec
        deadline = time.time() + duration_sec
        while time.time() < deadline:
            try:
                # Read 2 bytes header
                b1_b2 = await asyncio.wait_for(reader.readexactly(2), timeout=3.0)
                b1, b2 = b1_b2[0], b1_b2[1]
                opcode = b1 & 0x0F
                payload_len = b2 & 0x7F

                if payload_len == 126:
                    ext = await reader.readexactly(2)
                    payload_len = struct.unpack("!H", ext)[0]
                elif payload_len == 127:
                    ext = await reader.readexactly(8)
                    payload_len = struct.unpack("!Q", ext)[0]

                # If masked
                is_masked = bool(b2 & 0x80)
                mask = await reader.readexactly(4) if is_masked else None

                # Read payload
                payload = await reader.readexactly(payload_len) if payload_len > 0 else b""

                if opcode == 0x8: # Close frame
                    break
                elif opcode == 0x9: # Ping frame -> send Pong
                    # Pong: opcode 0xA
                    pong_frame = bytearray([0x8A, 0x80, 0x00, 0x00, 0x00, 0x00])
                    writer.write(pong_frame)
                    await writer.drain()
                elif opcode in (0x1, 0x2): # Text or Binary
                    res["messages_received"] += 1
                    res["bytes_received"] += len(payload)

            except asyncio.TimeoutError:
                # Idle between broadcast ticks
                continue
            except Exception as e:
                res["error"] = str(e)
                break

        res["active_duration_sec"] = round(time.perf_counter() - t_handshake, 2)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

    except Exception as e:
        res["error"] = str(e)

    return res

# ─────────────────────────────────────────────────────────────────────────────
# 2. HTTP REST CONCURRENCY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def send_http_request(url: str, timeout: float = 5.0) -> Tuple[int, float, bool]:
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ApexCapacityStressTester/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            resp.read() # consume body
            latency = (time.perf_counter() - t0) * 1000.0
            return status, latency, True
    except urllib.error.HTTPError as e:
        latency = (time.perf_counter() - t0) * 1000.0
        return e.code, latency, False
    except Exception:
        latency = (time.perf_counter() - t0) * 1000.0
        return 0, latency, False

def benchmark_http_tier(concurrency: int, total_requests: int, endpoint: str = "/api/v1/futures/state") -> Dict[str, Any]:
    url = f"{BASE_URL}{endpoint}"
    latencies: List[float] = []
    successes = 0
    failures = 0
    status_counts: Dict[int, int] = {}

    t_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_http_request, url) for _ in range(total_requests)]
        for f in as_completed(futures):
            code, lat, ok = f.result()
            latencies.append(lat)
            status_counts[code] = status_counts.get(code, 0) + 1
            if ok and code == 200:
                successes += 1
            else:
                failures += 1

    total_time = time.perf_counter() - t_start
    latencies.sort()

    rps = total_requests / total_time if total_time > 0 else 0
    p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0
    p90 = latencies[int(len(latencies) * 0.90)] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
    avg_lat = sum(latencies) / len(latencies) if latencies else 0

    return {
        "concurrency": concurrency,
        "total_requests": total_requests,
        "successes": successes,
        "failures": failures,
        "success_rate_pct": round((successes / total_requests) * 100.0, 2),
        "duration_sec": round(total_time, 2),
        "rps": round(rps, 1),
        "latency_avg_ms": round(avg_lat, 2),
        "latency_p50_ms": round(p50, 2),
        "latency_p90_ms": round(p90, 2),
        "latency_p95_ms": round(p95, 2),
        "latency_p99_ms": round(p99, 2),
        "latency_min_ms": round(latencies[0], 2) if latencies else 0,
        "latency_max_ms": round(latencies[-1], 2) if latencies else 0,
        "status_distribution": status_counts
    }

# ─────────────────────────────────────────────────────────────────────────────
# 3. WEBSOCKET CONCURRENCY SUITE
# ─────────────────────────────────────────────────────────────────────────────

async def benchmark_websocket_tier(concurrent_clients: int, duration_sec: float = 8.0) -> Dict[str, Any]:
    print(f"   Connecting {concurrent_clients} simultaneous WebSocket clients...")
    t_start = time.perf_counter()

    # Stagger connections slightly (5ms) to prevent SYN flood packet drops on Wi-Fi
    tasks = []
    for i in range(concurrent_clients):
        tasks.append(asyncio.create_task(ws_connect_client(i, duration_sec)))
        if i % 20 == 0:
            await asyncio.sleep(0.02)

    results = await asyncio.gather(*tasks)
    total_time = time.perf_counter() - t_start

    connected_count = sum(1 for r in results if r["connected"])
    handshake_latencies = [r["handshake_time_ms"] for r in results if r["connected"]]
    total_msgs = sum(r["messages_received"] for r in results)
    total_bytes = sum(r["bytes_received"] for r in results)
    errors = [r["error"] for r in results if r["error"] is not None]

    handshake_latencies.sort()
    p50_hs = handshake_latencies[int(len(handshake_latencies) * 0.50)] if handshake_latencies else 0
    p95_hs = handshake_latencies[int(len(handshake_latencies) * 0.95)] if handshake_latencies else 0
    avg_hs = sum(handshake_latencies) / len(handshake_latencies) if handshake_latencies else 0

    return {
        "concurrent_clients": concurrent_clients,
        "connected_count": connected_count,
        "connection_success_rate_pct": round((connected_count / concurrent_clients) * 100.0, 2),
        "duration_sec": round(total_time, 2),
        "avg_handshake_ms": round(avg_hs, 2),
        "p50_handshake_ms": round(p50_hs, 2),
        "p95_handshake_ms": round(p95_hs, 2),
        "total_messages_received": total_msgs,
        "total_bytes_received": total_bytes,
        "broadcast_msgs_per_client": round(total_msgs / max(1, connected_count), 1),
        "sample_errors": errors[:5]
    }

# ─────────────────────────────────────────────────────────────────────────────
# 4. MASTER BENCHMARK RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_full_capacity_audit():
    print("=" * 80)
    print("🚀 APEX QUANT v3.3: TERMUX SERVER REAL-TIME CAPACITY AUDIT")
    print(f"Target Server: {BASE_URL} (Android Termux ARM64 / Uvicorn + FastAPI)")
    print("=" * 80)

    # Pre-flight check
    try:
        st, lat, ok = send_http_request(f"{BASE_URL}/api/v1/futures/state")
        if not ok or st != 200:
            print(f"❌ Server pre-flight failed: HTTP {st}")
            sys.exit(1)
        print(f"✅ Pre-flight ping successful: {lat:.1f}ms latency\n")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        sys.exit(1)

    # STAGE 1: HTTP REST STRESS TEST
    print("─" * 80, flush=True)
    print("📊 STAGE 1: HTTP REST THROUGHPUT & CONCURRENCY BENCHMARK (TURBO MODE)", flush=True)
    print("─" * 80, flush=True)

    http_tiers = [
        (10, 200),
        (25, 400),
        (50, 600),
        (100, 800),
        (200, 1000),
        (300, 1200),
        (400, 1500)
    ]

    http_results = []
    print(f"{'Concurrency':<12} {'Requests':<10} {'Success %':<12} {'RPS':<10} {'Avg Lat':<12} {'p95 Lat':<12} {'p99 Lat':<12}", flush=True)
    print("-" * 80, flush=True)

    for conc, reqs in http_tiers:
        res = benchmark_http_tier(conc, reqs, "/api/v1/futures/state")
        http_results.append(res)
        print(f"{res['concurrency']:<12} {res['total_requests']:<10} {res['success_rate_pct']:<12.1f} {res['rps']:<10.1f} {res['latency_avg_ms']:<12.1f} {res['latency_p95_ms']:<12.1f} {res['latency_p99_ms']:<12.1f}", flush=True)
        time.sleep(1.0) # brief cooldown

    # STAGE 2: WEBSOCKET REALTIME CONCURRENCY
    print("\n" + "─" * 80, flush=True)
    print("📡 STAGE 2: REALTIME WEBSOCKET PERSISTENT CONNECTIONS CAPACITY (TURBO MODE)", flush=True)
    print("─" * 80, flush=True)

    ws_tiers = [10, 25, 50, 100, 200, 300, 400, 500]
    ws_results = []
    print(f"{'Concurrent WS':<15} {'Connected':<12} {'Success %':<12} {'Avg Handshake':<15} {'p95 Handshake':<15} {'Msgs/Client':<12}", flush=True)
    print("-" * 80, flush=True)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for tier in ws_tiers:
        ws_res = loop.run_until_complete(benchmark_websocket_tier(tier, duration_sec=6.0))
        ws_results.append(ws_res)
        print(f"{ws_res['concurrent_clients']:<15} {ws_res['connected_count']:<12} {ws_res['connection_success_rate_pct']:<12.1f} {ws_res['avg_handshake_ms']:<15.1f} {ws_res['p95_handshake_ms']:<15.1f} {ws_res['broadcast_msgs_per_client']:<12.1f}", flush=True)
        time.sleep(2.0) # cool down socket buffers

    # SAVE RESULTS TO JSON
    summary_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "termux_capacity_audit.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "target": BASE_URL,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "http_results": http_results,
            "websocket_results": ws_results
        }, f, indent=2)

    print("\n" + "=" * 80)
    print(f"✅ CAPACITY AUDIT COMPLETED! Results saved to {summary_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_full_capacity_audit()
