import 'package:shared_preferences/shared_preferences.dart';
import '../../core/constants/api_constants.dart';

class StorageService {
  static const String keyBaseUrl = "apex_base_url";
  static const String keySoundEnabled = "apex_sound_enabled";
  static const String keyAutoRefresh = "apex_auto_refresh";

  static Future<String> getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(keyBaseUrl) ?? ApiConstants.defaultBaseUrl;
  }

  static Future<void> setBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(keyBaseUrl, url);
  }

  static Future<bool> isSoundEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(keySoundEnabled) ?? true;
  }

  static Future<void> setSoundEnabled(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(keySoundEnabled, enabled);
  }
}