class ApiConstants {
  // Default Live Server URL
  static const String defaultBaseUrl = "https://apex.xrinvest.uz";
  static const String defaultLocalUrl = "http://192.168.1.136:8000";

  // Endpoints
  static const String healthEndpoint = "/api/v1/system/health";
  static const String liveSignalsEndpoint = "/api/v1/signals/live";
  static const String signalsHistoryEndpoint = "/api/v1/signals/history";
  static const String scanNowEndpoint = "/api/v1/signals/scan-now";
  static const String livePositionsEndpoint = "/api/v1/positions/live";
  static const String liveEquityEndpoint = "/api/v1/portfolio/live-equity";
  static const String panicCloseEndpoint = "/api/v1/positions/panic-close";
  static const String resetPositionsEndpoint = "/api/v1/positions/reset";
  static const String klinesEndpoint = "/api/v1/market/klines";
  static const String engineStatsEndpoint = "/api/v1/engine/stats";
  static const String forceEngineScanEndpoint = "/api/v1/engine/force-scan";

  // Binance Public WebSocket URL for Real-Time Streaming
  static const String binanceWsBase = "wss://stream.binance.com:9443/ws";
}