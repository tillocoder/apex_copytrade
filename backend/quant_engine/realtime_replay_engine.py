from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set

from .config import EngineConfig, EngineMode
from .market_data import MarketDataEngine, Candle, MarketEvent, SYMBOL_SPECS
from .backtest import BacktestEngine, BacktestRunResult

class EventIngestionBuffer:
    """
    Deterministic Event Ingestion Buffer.
    Handles out-of-order WebSocket arrivals, duplicate events, and multi-symbol
    buffering by maintaining strict canonical sorting:
    (timestamp ASC, symbol ASC, timeframe ASC, sequence_id ASC).
    """

    def __init__(self):
        self._buffer: List[MarketEvent] = []
        self._seen_event_keys: Set[Tuple[datetime, str, int]] = set()

    def push(self, event: MarketEvent) -> bool:
        """Pushes an event. Deduplicates identical (timestamp, symbol, sequence_id). Returns True if added."""
        dedup_key = (event.timestamp, event.symbol, event.sequence_id)
        if dedup_key in self._seen_event_keys:
            return False
        self._seen_event_keys.add(dedup_key)
        self._buffer.append(event)
        return True

    def push_batch(self, events: List[MarketEvent]) -> int:
        added = 0
        for ev in events:
            if self.push(ev):
                added += 1
        return added

    def flush_canonical(self) -> List[MarketEvent]:
        """Returns all buffered events in deterministic canonical order and clears the buffer."""
        sorted_events = sorted(self._buffer, key=lambda e: e.canonical_key)
        self._buffer = []
        return sorted_events

    def get_canonical_events(self) -> List[MarketEvent]:
        """Returns sorted events without clearing buffer."""
        return sorted(self._buffer, key=lambda e: e.canonical_key)


class RealtimeReplayEngine:
    """
    Production-grade Realtime Engine Replay Mode.
    Uses ONE shared canonical market event processing pipeline with BacktestEngine.
    Enforces exact deterministic execution and computes event-by-event state SHA-256 hashes.
    """

    def __init__(self, config: EngineConfig):
        self.config = config
        self.ingestion_buffer = EventIngestionBuffer()

    def process_candle_stream(self, candles: List[Candle]) -> Tuple[BacktestRunResult, List[Dict[str, Any]]]:
        """
        Processes a list of candles in Realtime Replay mode.
        Sorts inputs through EventIngestionBuffer into canonical MarketEvent order.
        Returns (BacktestRunResult, event_state_logs).
        """
        self.ingestion_buffer = EventIngestionBuffer()
        events = []
        for idx, c in enumerate(candles):
            events.append(MarketEvent(
                timestamp=c.timestamp,
                symbol=c.symbol,
                timeframe=self.config.strategy.timeframe,
                sequence_id=idx,
                event_type="CANDLE_CLOSE",
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
                raw_candle=c
            ))

        self.ingestion_buffer.push_batch(events)
        canonical_events = self.ingestion_buffer.flush_canonical()

        # Run BacktestEngine with canonical MarketDataEngine
        market_engine = MarketDataEngine()
        canonical_candles = [e.raw_candle for e in canonical_events if e.raw_candle is not None]
        market_engine.load_from_candles(canonical_candles)
        
        # Populate multi_candles in sorted symbol order
        multi_map: Dict[str, List[Candle]] = {}
        for c in canonical_candles:
            if c.symbol not in multi_map:
                multi_map[c.symbol] = []
            multi_map[c.symbol].append(c)
        market_engine.multi_candles = multi_map

        bt_engine = BacktestEngine(self.config)
        run_res = bt_engine.run(market_engine)

        # Build event-level state logs
        event_logs = self._generate_event_state_logs(canonical_events, run_res)
        return run_res, event_logs

    def _generate_event_state_logs(self, events: List[MarketEvent], run_res: BacktestRunResult) -> List[Dict[str, Any]]:
        """Computes deterministic SHA-256 state hashes for every event."""
        event_logs = []
        
        # Index trade logs by symbol and exit time or entry time for quick signal/order state mapping
        trade_logs = run_res.trade_logs
        
        for idx, ev in enumerate(events):
            event_id = f"EVT_{idx+1:06d}"
            
            # Find signals or orders for this event timestamp/symbol
            matched_trades = [t for t in trade_logs if t["symbol"] == ev.symbol and (t["entry_time"] == ev.timestamp.isoformat() or t["exit_time"] == ev.timestamp.isoformat())]
            
            signal_str = matched_trades[0]["side"] if matched_trades else "NONE"
            pos_str = f"{matched_trades[0]['side']}@{matched_trades[0]['entry_price']}" if matched_trades else "FLAT"
            order_str = f"{matched_trades[0]['reason']}" if matched_trades else "NONE"

            # Compute state dict
            state_dict = {
                "event_id": event_id,
                "timestamp": ev.timestamp.isoformat(),
                "symbol": ev.symbol,
                "sequence_id": ev.sequence_id,
                "open": round(ev.open, 4),
                "high": round(ev.high, 4),
                "low": round(ev.low, 4),
                "close": round(ev.close, 4),
                "signal": signal_str,
                "position": pos_str,
                "order": order_str
            }
            
            state_json = json.dumps(state_dict, sort_keys=True)
            state_hash = hashlib.sha256(state_json.encode('utf-8')).hexdigest()[:12]

            event_logs.append({
                "event_id": event_id,
                "timestamp": ev.timestamp.isoformat(),
                "symbol": ev.symbol,
                "sequence_id": ev.sequence_id,
                "state_hash": state_hash,
                "signal": signal_str,
                "position": pos_str,
                "order": order_str
            })

        return event_logs
