class SystemHealthModel {
  final String vpsStatus;
  final int vpsLatency;
  final String exchangeApiStatus;
  final int exchangeLatency;
  final String dbStatus;
  final String wsStatus;
  final String pythonEngineStatus;
  final String aiEngineStatus;

  SystemHealthModel({
    required this.vpsStatus,
    required this.vpsLatency,
    required this.exchangeApiStatus,
    required this.exchangeLatency,
    required this.dbStatus,
    required this.wsStatus,
    required this.pythonEngineStatus,
    required this.aiEngineStatus,
  });

  factory SystemHealthModel.fromJson(Map<String, dynamic> json) {
    return SystemHealthModel(
      vpsStatus: json['vpsStatus']?.toString() ?? 'ONLINE',
      vpsLatency: int.tryParse(json['vpsLatency']?.toString() ?? '120') ?? 120,
      exchangeApiStatus: json['exchangeApiStatus']?.toString() ?? 'CONNECTED',
      exchangeLatency: int.tryParse(json['exchangeLatency']?.toString() ?? '45') ?? 45,
      dbStatus: json['dbStatus']?.toString() ?? 'HEALTHY',
      wsStatus: json['wsStatus']?.toString() ?? 'STREAMING',
      pythonEngineStatus: json['pythonEngineStatus']?.toString() ?? 'RUNNING',
      aiEngineStatus: json['aiEngineStatus']?.toString() ?? 'ACTIVE',
    );
  }

  bool get isHealthy => vpsStatus == 'ONLINE' && pythonEngineStatus == 'RUNNING';
}