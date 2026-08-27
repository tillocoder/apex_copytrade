import 'dart:async';
import 'package:flutter/material.dart';
import '../data/models/position_model.dart';
import '../data/services/api_service.dart';

class TradesProvider with ChangeNotifier {
  final ApiService apiService;

  List<PositionModel> openPositions = [];
  PositionModel? selectedPosition;
  bool isLoading = false;
  bool isClosing = false;
  Timer? _pollTimer;

  TradesProvider(this.apiService) {
    loadPositions();
    _pollTimer = Timer.periodic(const Duration(seconds: 4), (_) => loadPositions(silent: true));
  }

  Future<void> loadPositions({bool silent = false}) async {
    if (!silent) {
      isLoading = true;
      notifyListeners();
    }

    try {
      final list = await apiService.fetchLivePositions();
      openPositions = list.where((p) => p.status == 'OPEN' || p.status == 'PARTIAL').toList();

      if (selectedPosition == null && openPositions.isNotEmpty) {
        selectedPosition = openPositions.first;
      }
    } catch (_) {}

    if (!silent) {
      isLoading = false;
    }
    notifyListeners();
  }

  void selectPosition(PositionModel pos) {
    selectedPosition = pos;
    notifyListeners();
  }

  Future<bool> panicCloseAll() async {
    isClosing = true;
    notifyListeners();
    final ok = await apiService.panicCloseAll();
    await Future.delayed(const Duration(seconds: 1));
    await loadPositions();
    isClosing = false;
    notifyListeners();
    return ok;
  }

  Future<bool> resetPositions() async {
    isClosing = true;
    notifyListeners();
    final ok = await apiService.resetPositions();
    await Future.delayed(const Duration(seconds: 1));
    await loadPositions();
    isClosing = false;
    notifyListeners();
    return ok;
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}