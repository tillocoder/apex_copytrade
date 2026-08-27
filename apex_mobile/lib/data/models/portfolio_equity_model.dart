class EquityPoint {
  final String timestamp;
  final double equity;

  EquityPoint({required this.timestamp, required this.equity});

  factory EquityPoint.fromJson(Map<String, dynamic> json) {
    return EquityPoint(
      timestamp: json['timestamp']?.toString() ?? '',
      equity: double.tryParse(json['equity']?.toString() ?? '10000') ?? 10000.0,
    );
  }
}

class PortfolioEquityModel {
  final double initialCapital;
  final double currentEquity;
  final double totalRealizedPnl;
  final double totalUnrealizedPnl;
  final double winRate;
  final int totalTrades;
  final int winningTrades;
  final int losingTrades;
  final double profitFactor;
  final double maxDrawdown;
  final List<EquityPoint> equityCurve;

  PortfolioEquityModel({
    required this.initialCapital,
    required this.currentEquity,
    required this.totalRealizedPnl,
    required this.totalUnrealizedPnl,
    required this.winRate,
    required this.totalTrades,
    required this.winningTrades,
    required this.losingTrades,
    required this.profitFactor,
    required this.maxDrawdown,
    required this.equityCurve,
  });

  factory PortfolioEquityModel.fromJson(Map<String, dynamic> json) {
    var curve = <EquityPoint>[];
    if (json['liveEquityCurve'] is List) {
      curve = (json['liveEquityCurve'] as List)
          .map((item) => EquityPoint.fromJson(item as Map<String, dynamic>))
          .toList();
    }

    return PortfolioEquityModel(
      initialCapital: double.tryParse(json['initialCapital']?.toString() ?? '10000') ?? 10000.0,
      currentEquity: double.tryParse(json['currentEquity']?.toString() ?? '10000') ?? 10000.0,
      totalRealizedPnl: double.tryParse(json['totalRealizedPnl']?.toString() ?? '0') ?? 0.0,
      totalUnrealizedPnl: double.tryParse(json['totalUnrealizedPnl']?.toString() ?? '0') ?? 0.0,
      winRate: double.tryParse(json['winRate']?.toString() ?? '0') ?? 0.0,
      totalTrades: int.tryParse(json['totalTrades']?.toString() ?? '0') ?? 0,
      winningTrades: int.tryParse(json['winningTrades']?.toString() ?? '0') ?? 0,
      losingTrades: int.tryParse(json['losingTrades']?.toString() ?? '0') ?? 0,
      profitFactor: double.tryParse(json['profitFactor']?.toString() ?? '1.0') ?? 1.0,
      maxDrawdown: double.tryParse(json['maxDrawdown']?.toString() ?? '0') ?? 0.0,
      equityCurve: curve,
    );
  }

  double get pnlPercent => initialCapital > 0 ? (totalRealizedPnl / initialCapital) * 100 : 0.0;
}