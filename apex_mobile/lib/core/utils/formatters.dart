import 'package:intl/intl.dart';

class Formatters {
  static final NumberFormat _currencyFmt = NumberFormat.currency(symbol: r'$', decimalDigits: 2);

  static String currency(dynamic value) {
    if (value == null) return r'$0.00';
    final numVal = double.tryParse(value.toString()) ?? 0.0;
    return _currencyFmt.format(numVal);
  }

  static String price(dynamic value, [int decimals = 2]) {
    if (value == null) return '0.00';
    final numVal = double.tryParse(value.toString()) ?? 0.0;
    return numVal.toStringAsFixed(decimals);
  }

  static String percent(dynamic value, [bool showPlus = true]) {
    if (value == null) return '0.00%';
    final numVal = double.tryParse(value.toString()) ?? 0.0;
    final sign = (numVal > 0 && showPlus) ? '+' : '';
    return '$sign${numVal.toStringAsFixed(2)}%';
  }

  static String formatTimestamp(dynamic timestamp) {
    if (timestamp == null) return '';
    try {
      final double sec = double.tryParse(timestamp.toString()) ?? 0.0;
      final dt = DateTime.fromMillisecondsSinceEpoch((sec * 1000).toInt(), isUtc: true);
      return DateFormat('yyyy-MM-dd HH:mm').format(dt.toLocal());
    } catch (_) {
      return '';
    }
  }
}