import 'dart:async';
import 'package:flutter/material.dart';
import '../data/models/signal_model.dart';
import '../data/services/api_service.dart';

class SignalsProvider with ChangeNotifier {
  final ApiService apiService;

  List<SignalModel> activeSignals = [];
  List<SignalModel> historySignals = [];
  SignalModel? selectedSignal;
  bool isLoading = false;
  bool isScanning = false;
  Timer? _pollTimer;

  SignalsProvider(this.apiService) {
    loadSignals();
    _pollTimer = Timer.periodic(const Duration(seconds: 6), (_) => loadSignals(silent: true));
  }

  Future<void> loadSignals({bool silent = false}) async {
    if (!silent) {
      isLoading = true;
      notifyListeners();
    }

    try {
      final live = await apiService.fetchLiveSignals();
      final hist = await apiService.fetchSignalsHistory();
      
      activeSignals = live.where((s) => s.isActive).toList();
      historySignals = hist;

      if (selectedSignal == null && activeSignals.isNotEmpty) {
        selectedSignal = activeSignals.first;
      }
    } catch (_) {}

    if (!silent) {
      isLoading = false;
    }
    notifyListeners();
  }

  void selectSignal(SignalModel signal) {
    selectedSignal = signal;
    notifyListeners();
  }

  Future<bool> triggerScanNow() async {
    isScanning = true;
    notifyListeners();
    final ok = await apiService.triggerScanNow();
    await Future.delayed(const Duration(seconds: 2));
    await loadSignals();
    isScanning = false;
    notifyListeners();
    return ok;
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}