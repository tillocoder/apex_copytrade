import 'dart:async';
import 'package:flutter/material.dart';
import '../data/models/system_health_model.dart';
import '../data/models/portfolio_equity_model.dart';
import '../data/services/api_service.dart';
import '../data/services/websocket_service.dart';
import '../data/services/storage_service.dart';

class TerminalProvider with ChangeNotifier {
  final ApiService apiService = ApiService();
  final WebSocketService wsService = WebSocketService();

  SystemHealthModel health = SystemHealthModel(
    vpsStatus: 'ONLINE',
    vpsLatency: 120,
    exchangeApiStatus: 'CONNECTED',
    exchangeLatency: 45,
    dbStatus: 'HEALTHY',
    wsStatus: 'STREAMING',
    pythonEngineStatus: 'RUNNING',
    aiEngineStatus: 'ACTIVE',
  );

  PortfolioEquityModel portfolio = PortfolioEquityModel(
    initialCapital: 10000,
    currentEquity: 10000,
    totalRealizedPnl: 0,
    totalUnrealizedPnl: 0,
    winRate: 0,
    totalTrades: 0,
    winningTrades: 0,
    losingTrades: 0,
    profitFactor: 1.0,
    maxDrawdown: 0,
    equityCurve: [],
  );

  Map<String, BinanceTicker> tickers = {
    'BTC/USDT': BinanceTicker(symbol: 'BTC/USDT', price: 78500.0, change24h: 1.2),
    'ETH/USDT': BinanceTicker(symbol: 'ETH/USDT', price: 2450.0, change24h: -0.5),
  };

  int selectedTab = 0;
  bool isRefreshing = false;
  Timer? _timer;

  TerminalProvider() {
    _init();
  }

  void _init() async {
    final savedUrl = await StorageService.getBaseUrl();
    apiService.updateBaseUrl(savedUrl);
    
    // Connect WebSocket
    wsService.connect();
    wsService.tickerStream.listen((ticker) {
      tickers[ticker.symbol] = ticker;
      notifyListeners();
    });

    refreshAll();

    // Auto-poll every 5 seconds
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => refreshAll(silent: true));
  }

  Future<void> refreshAll({bool silent = false}) async {
    if (!silent) {
      isRefreshing = true;
      notifyListeners();
    }

    try {
      final h = await apiService.fetchHealth();
      final p = await apiService.fetchPortfolioEquity();
      health = h;
      portfolio = p;
    } catch (_) {}

    if (!silent) {
      isRefreshing = false;
    }
    notifyListeners();
  }

  void setTab(int index) {
    selectedTab = index;
    notifyListeners();
  }

  @override
  void dispose() {
    _timer?.cancel();
    wsService.disconnect();
    super.dispose();
  }
}