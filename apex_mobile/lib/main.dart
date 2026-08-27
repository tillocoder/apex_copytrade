import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/theme/apex_theme.dart';
import 'core/theme/apex_colors.dart';
import 'state/terminal_provider.dart';
import 'state/signals_provider.dart';
import 'state/trades_provider.dart';
import 'presentation/screens/home_screen.dart';
import 'presentation/screens/signals_screen.dart';
import 'presentation/screens/trades_screen.dart';
import 'presentation/screens/settings_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ApexTradingApp());
}

class ApexTradingApp extends StatelessWidget {
  const ApexTradingApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => TerminalProvider()),
        ChangeNotifierProxyProvider<TerminalProvider, SignalsProvider>(
          create: (ctx) => SignalsProvider(ctx.read<TerminalProvider>().apiService),
          update: (_, term, prev) => prev ?? SignalsProvider(term.apiService),
        ),
        ChangeNotifierProxyProvider<TerminalProvider, TradesProvider>(
          create: (ctx) => TradesProvider(ctx.read<TerminalProvider>().apiService),
          update: (_, term, prev) => prev ?? TradesProvider(term.apiService),
        ),
      ],
      child: MaterialApp(
        title: 'Apex Institutional Terminal',
        debugShowCheckedModeBanner: false,
        theme: ApexTheme.darkTheme,
        home: const MainShell(),
      ),
    );
  }
}

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    HomeScreen(),
    SignalsScreen(),
    TradesScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: ApexColors.border, width: 1)),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (index) => setState(() => _currentIndex = index),
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.dashboard_outlined),
              activeIcon: Icon(Icons.dashboard),
              label: 'Overview',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.auto_awesome_outlined),
              activeIcon: Icon(Icons.auto_awesome),
              label: 'AI Signals',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.layers_outlined),
              activeIcon: Icon(Icons.layers),
              label: 'Trades',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.settings_outlined),
              activeIcon: Icon(Icons.settings),
              label: 'Settings',
            ),
          ],
        ),
      ),
    );
  }
}