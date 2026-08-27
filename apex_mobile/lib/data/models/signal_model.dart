class VerificationItem {
  final String label;
  final bool passed;

  VerificationItem({required this.label, required this.passed});

  factory VerificationItem.fromJson(Map<String, dynamic> json) {
    return VerificationItem(
      label: json['label']?.toString() ?? '',
      passed: json['passed'] == true,
    );
  }
}

class SignalModel {
  final String id;
  final String symbol;
  final String side; // BUY or SELL
  final String timeframe;
  final String setupType;
  final String regime;
  final double entry;
  final double sl;
  final double tp1;
  final double tp2;
  final double tp3;
  final double rr;
  final double quantScore;
  final double aiReviewScore;
  final double factorScore;
  final double confidence;
  final String status; // CONFIRMED, PENDING, TP1_HIT, TP2_HIT, TP_HIT, SL_HIT, EXPIRED
  final String reasoning;
  final String aiNotes;
  final double timestamp;
  final String formattedTime;
  final List<VerificationItem> verification;
  final Map<String, dynamic> indicators;
  final int? telegramMessageId;

  SignalModel({
    required this.id,
    required this.symbol,
    required this.side,
    required this.timeframe,
    required this.setupType,
    required this.regime,
    required this.entry,
    required this.sl,
    required this.tp1,
    required this.tp2,
    required this.tp3,
    required this.rr,
    required this.quantScore,
    required this.aiReviewScore,
    required this.factorScore,
    required this.confidence,
    required this.status,
    required this.reasoning,
    required this.aiNotes,
    required this.timestamp,
    required this.formattedTime,
    required this.verification,
    required this.indicators,
    this.telegramMessageId,
  });

  factory SignalModel.fromJson(Map<String, dynamic> json) {
    var vList = <VerificationItem>[];
    if (json['verification'] is List) {
      vList = (json['verification'] as List)
          .map((item) => VerificationItem.fromJson(item as Map<String, dynamic>))
          .toList();
    }

    return SignalModel(
      id: json['id']?.toString() ?? '',
      symbol: json['symbol']?.toString() ?? 'BTC/USDT',
      side: json['side']?.toString().toUpperCase() ?? 'BUY',
      timeframe: json['timeframe']?.toString() ?? 'M15',
      setupType: json['setupType']?.toString() ?? 'SMART_MONEY',
      regime: json['regime']?.toString() ?? 'TRENDING',
      entry: double.tryParse(json['entry']?.toString() ?? '0') ?? 0.0,
      sl: double.tryParse(json['sl']?.toString() ?? '0') ?? 0.0,
      tp1: double.tryParse(json['tp1']?.toString() ?? json['tp']?.toString() ?? '0') ?? 0.0,
      tp2: double.tryParse(json['tp2']?.toString() ?? '0') ?? 0.0,
      tp3: double.tryParse(json['tp3']?.toString() ?? '0') ?? 0.0,
      rr: double.tryParse(json['rr']?.toString() ?? '2.5') ?? 2.5,
      quantScore: double.tryParse(json['quantScore']?.toString() ?? json['aiScore']?.toString() ?? '75') ?? 75.0,
      aiReviewScore: double.tryParse(json['aiReviewScore']?.toString() ?? '75') ?? 75.0,
      factorScore: double.tryParse(json['factorScore']?.toString() ?? '85') ?? 85.0,
      confidence: double.tryParse(json['confidence']?.toString() ?? '80') ?? 80.0,
      status: json['status']?.toString().toUpperCase() ?? 'CONFIRMED',
      reasoning: json['reasoning']?.toString() ?? 'Smart Money Liquidity Sweep and Structure Alignment.',
      aiNotes: json['aiNotes']?.toString() ?? '',
      timestamp: double.tryParse(json['timestamp']?.toString() ?? '0') ?? 0.0,
      formattedTime: json['formatted_time']?.toString() ?? '',
      verification: vList,
      indicators: json['indicators'] is Map<String, dynamic> ? json['indicators'] : {},
      telegramMessageId: json['telegram_message_id'] is int ? json['telegram_message_id'] : null,
    );
  }

  bool get isBuy => side == 'BUY';
  bool get isActive => status == 'CONFIRMED' || status == 'PENDING' || status == 'ACTIVE' || status == 'OPEN' || status == 'TP1_HIT' || status == 'TP2_HIT';
}