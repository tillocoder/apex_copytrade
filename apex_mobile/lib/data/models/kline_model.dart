class KlineModel {
  final int timestamp;
  final String time;
  final double open;
  final double high;
  final double low;
  final double close;
  final double volume;
  final bool isUp;

  KlineModel({
    required this.timestamp,
    required this.time,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    required this.volume,
    required this.isUp,
  });

  factory KlineModel.fromJson(Map<String, dynamic> json) {
    final o = double.tryParse(json['open']?.toString() ?? '0') ?? 0.0;
    final c = double.tryParse(json['close']?.toString() ?? '0') ?? 0.0;
    return KlineModel(
      timestamp: int.tryParse(json['timestamp']?.toString() ?? '0') ?? 0,
      time: json['time']?.toString() ?? '',
      open: o,
      high: double.tryParse(json['high']?.toString() ?? '0') ?? 0.0,
      low: double.tryParse(json['low']?.toString() ?? '0') ?? 0.0,
      close: c,
      volume: double.tryParse(json['volume']?.toString() ?? '0') ?? 0.0,
      isUp: json['isUp'] == true || (c >= o),
    );
  }
}