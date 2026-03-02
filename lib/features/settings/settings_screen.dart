import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';
import '../../app/theme.dart';
import '../../shared/api/client.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final TextEditingController _spDcController = TextEditingController();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  final SaveTuneApi _api = SaveTuneApi();
  
  bool _isLoading = false;
  bool _obscureText = true;
  bool _isConnected = false;

  @override
  void initState() {
    super.initState();
    _checkConnection();
  }

  Future<void> _checkConnection() async {
    final savedSpDc = await _storage.read(key: 'sp_dc');
    if (savedSpDc != null && savedSpDc.isNotEmpty) {
      if (mounted) {
        setState(() {
          _isConnected = true;
          _spDcController.text = savedSpDc;
        });
      }
    }
  }

  Future<void> _validateAndSave() async {
    if (_spDcController.text.isEmpty) return;
    
    setState(() => _isLoading = true);
    try {
      await _api.validateSpDc(_spDcController.text);
      await _storage.write(key: 'sp_dc', value: _spDcController.text);
      if (mounted) {
        setState(() => _isConnected = true);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('✓ Connected to Spotify!'), backgroundColor: Colors.green),
        );
        Future.delayed(const Duration(seconds: 1), () {
          if (mounted) context.go('/search');
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_isConnected)
              Container(
                padding: const EdgeInsets.all(12),
                color: Colors.green.shade900,
                child: const Row(
                  children: [
                    Icon(Icons.check_circle, color: Colors.white),
                    SizedBox(width: 8),
                    Text('Currently connected', style: TextStyle(color: Colors.white)),
                  ],
                ),
              ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _spDcController,
              obscureText: _obscureText,
              maxLines: 1,
              decoration: InputDecoration(
                labelText: 'Spotify sp_dc Cookie',
                hintText: 'Paste your sp_dc cookie value here...',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: Icon(_obscureText ? Icons.visibility : Icons.visibility_off),
                  onPressed: () => setState(() => _obscureText = !_obscureText),
                ),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _isLoading ? null : _validateAndSave,
              style: ElevatedButton.styleFrom(
                backgroundColor: SaveTuneTheme.primaryColor,
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: _isLoading
                  ? const CircularProgressIndicator(color: Colors.white)
                  : Text(_isConnected ? 'Update & Save' : 'Validate & Save', style: const TextStyle(fontSize: 16, color: Colors.white)),
            ),
            const SizedBox(height: 32),
            Card(
              color: SaveTuneTheme.surfaceColor,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text('HOW TO GET YOUR sp_dc', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    SizedBox(height: 12),
                    ListTile(leading: Icon(Icons.language), title: Text('1. Open Chrome → go to open.spotify.com → log in')),
                    ListTile(leading: Icon(Icons.code), title: Text('2. Press F12 to open Developer Tools')),
                    ListTile(leading: Icon(Icons.folder), title: Text('3. Click "Application" tab in DevTools')),
                    ListTile(leading: Icon(Icons.cookie), title: Text('4. Click "Cookies" → click "https://open.spotify.com"')),
                    ListTile(leading: Icon(Icons.search), title: Text('5. Find the cookie named exactly: sp_dc')),
                    ListTile(leading: Icon(Icons.copy), title: Text('6. Click on it → copy the ENTIRE Value field')),
                    ListTile(leading: Icon(Icons.paste), title: Text('7. Paste it above → tap Validate')),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
