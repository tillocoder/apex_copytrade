import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class BinanceTicker {
  final String symbol;
  final double price;
  final double change24h;

  BinanceTicker({required this.symbol, required this.price, required this.change24h});
}

class WebSocketService {
  WebSocketChannel? _channel;
  final _tickerStreamController = StreamController<BinanceTicker>.broadcast();

  Stream<BinanceTicker> get tickerStream => _tickerStreamController.stream;

  void connect() {
    try {
      // Subscribe to BTC and ETH real-time mini-tickers
      final uri = Uri.parse("wss://stream.binance.com:9443/ws/btcusdt@miniTicker/ethusdt@miniTicker");
      _channel = WebSocketChannel.connect(uri);

      _channel!.stream.listen((message) {
        try {
          final data = jsonDecode(message);
          final symRaw = data['s']?.toString().toUpperCase() ?? '';
          final sym = symRaw == 'BTCUSDT' ? 'BTC/USDT' : symRaw == 'ETHUSDT' ? 'ETH/USDT' : symRaw;
          final p = double.tryParse(data['c']?.toString() ?? '0') ?? 0.0;
          final o = double.tryParse(data['o']?.toString() ?? '0') ?? 0.0;
          final change24h = o > 0 ? ((p - o) / o) * 100 : 0.0;

          if (sym.isNotEmpty && p > 0) {
            _tickerStreamController.add(BinanceTicker(symbol: sym, price: p, change24h: change24h));
          }
        } catch (_) {}
      }, onError: (err) {
        print('WebSocket error: $err');
      }, onDone: () {
        // Reconnect after delay
        Future.delayed(const Duration(seconds: 5), connect);
      });
    } catch (e) {
      print('Failed to connect WebSocket: $e');
    }
  }

  void disconnect() {
    _channel?.sink.close();
    _channel = null;
  }
}