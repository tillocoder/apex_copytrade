class PositionModel {
  final String id;
  final String account;
  final String symbol;
  final String side;
  final double entryPrice;
  final double currentPrice;
  final double size;
  final int leverage;
  final double marginUsed;
  final double unrealizedPnl;
  final double unrealizedPnlPercent;
  final double sl;
  final double tp1;
  final double tp2;
  final double tp3;
  final double breakEvenPrice;
  final bool trailingStopActive;
  final double atr;
  final double riskPercent;
  final double rewardPercent;
  final double liquidationPrice;
  final String duration;
  final String timeOpen;
  final String aiExplanation;
  final double aiConfidence;
  final String aiRecommendation;
  final String status;

  PositionModel({
    required this.id,
    required this.account,
    required this.symbol,
    required this.side,
    required this.entryPrice,
    required this.currentPrice,
    required this.size,
    required this.leverage,
    required this.marginUsed,
    required this.unrealizedPnl,
    required this.unrealizedPnlPercent,
    required this.sl,
    required this.tp1,
    required this.tp2,
    required this.tp3,
    required this.breakEvenPrice,
    required this.trailingStopActive,
    required this.atr,
    required this.riskPercent,
    required this.rewardPercent,
    required this.liquidationPrice,
    required this.duration,
    required this.timeOpen,
    required this.aiExplanation,
    required this.aiConfidence,
    required this.aiRecommendation,
    required this.status,
  });

  factory PositionModel.fromJson(Map<String, dynamic> json) {
    return PositionModel(
      id: json['id']?.toString() ?? '',
      account: json['account']?.toString() ?? 'REAL BINANCE DATA',
      symbol: json['symbol']?.toString() ?? 'BTC/USDT',
      side: json['side']?.toString().toUpperCase() ?? 'BUY',
      entryPrice: double.tryParse(json['entryPrice']?.toString() ?? '0') ?? 0.0,
      currentPrice: double.tryParse(json['currentPrice']?.toString() ?? '0') ?? 0.0,
      size: double.tryParse(json['size']?.toString() ?? '0') ?? 0.0,
      leverage: int.tryParse(json['leverage']?.toString() ?? '2') ?? 2,
      marginUsed: double.tryParse(json['marginUsed']?.toString() ?? '0') ?? 0.0,
      unrealizedPnl: double.tryParse(json['unrealizedPnl']?.toString() ?? '0') ?? 0.0,
      unrealizedPnlPercent: double.tryParse(json['unrealizedPnlPercent']?.toString() ?? '0') ?? 0.0,
      sl: double.tryParse(json['sl']?.toString() ?? '0') ?? 0.0,
      tp1: double.tryParse(json['tp1']?.toString() ?? '0') ?? 0.0,
      tp2: double.tryParse(json['tp2']?.toString() ?? '0') ?? 0.0,
      tp3: double.tryParse(json['tp3']?.toString() ?? '0') ?? 0.0,
      breakEvenPrice: double.tryParse(json['breakEvenPrice']?.toString() ?? '0') ?? 0.0,
      trailingStopActive: json['trailingStopActive'] == true,
      atr: double.tryParse(json['atr']?.toString() ?? '0') ?? 0.0,
      riskPercent: double.tryParse(json['riskPercent']?.toString() ?? '1.0') ?? 1.0,
      rewardPercent: double.tryParse(json['rewardPercent']?.toString() ?? '2.0') ?? 2.0,
      liquidationPrice: double.tryParse(json['liquidationPrice']?.toString() ?? '0') ?? 0.0,
      duration: json['duration']?.toString() ?? '0h 15m',
      timeOpen: json['timeOpen']?.toString() ?? '12:00 UTC',
      aiExplanation: json['aiExplanation']?.toString() ?? '',
      aiConfidence: double.tryParse(json['aiConfidence']?.toString() ?? '75') ?? 75.0,
      aiRecommendation: json['aiRecommendation']?.toString() ?? 'HOLD',
      status: json['status']?.toString().toUpperCase() ?? 'OPEN',
    );
  }

  bool get isBuy => side == 'BUY';
  bool get isProfit => unrealizedPnl >= 0;
}