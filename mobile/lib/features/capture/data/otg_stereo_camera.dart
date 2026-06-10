import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

class OtgUsbCamera {
  const OtgUsbCamera({
    required this.deviceName,
    required this.vendorId,
    required this.productId,
    required this.hasPermission,
    this.manufacturerName,
    this.productName,
    this.deviceClass,
  });

  final String deviceName;
  final int vendorId;
  final int productId;
  final bool hasPermission;
  final String? manufacturerName;
  final String? productName;
  final int? deviceClass;

  factory OtgUsbCamera.fromMap(Map<dynamic, dynamic> map) => OtgUsbCamera(
        deviceName: map['deviceName'] as String? ?? '',
        vendorId: map['vendorId'] as int? ?? 0,
        productId: map['productId'] as int? ?? 0,
        hasPermission: map['hasPermission'] as bool? ?? false,
        manufacturerName: map['manufacturerName'] as String?,
        productName: map['productName'] as String?,
        deviceClass: map['deviceClass'] as int?,
      );

  String get label {
    final name = productName?.trim().isNotEmpty == true
        ? productName!.trim()
        : deviceName;
    final maker = manufacturerName?.trim();
    return maker == null || maker.isEmpty ? name : '$maker $name';
  }
}

class OtgStereoFrame {
  const OtgStereoFrame({
    required this.leftJpeg,
    required this.width,
    required this.height,
    required this.sideBySide,
    this.rightJpeg,
  });

  final Uint8List leftJpeg;
  final Uint8List? rightJpeg;
  final int width;
  final int height;
  final bool sideBySide;

  bool get hasRightFrame => rightJpeg != null;

  factory OtgStereoFrame.fromMap(Map<dynamic, dynamic> map) => OtgStereoFrame(
        leftJpeg: map['leftJpeg'] as Uint8List,
        rightJpeg: map['rightJpeg'] as Uint8List?,
        width: map['width'] as int? ?? 0,
        height: map['height'] as int? ?? 0,
        sideBySide: map['sideBySide'] as bool? ?? false,
      );
}

class OtgStereoCamera {
  const OtgStereoCamera();

  static const MethodChannel _channel =
      MethodChannel('zmetrics/otg_stereo_camera');

  Future<List<OtgUsbCamera>> listUsbCameras() async {
    if (kIsWeb) return const [];
    final raw = await _channel.invokeListMethod<dynamic>('listUsbCameras');
    return (raw ?? const [])
        .whereType<Map<dynamic, dynamic>>()
        .map(OtgUsbCamera.fromMap)
        .toList(growable: false);
  }

  Future<OtgStereoFrame> captureFrame() async {
    if (kIsWeb) {
      throw UnsupportedError('OTG camera capture is available only on Android');
    }
    final raw = await _channel.invokeMapMethod<dynamic, dynamic>(
      'captureStereoFrame',
      {'splitSideBySide': true},
    );
    if (raw == null) {
      throw StateError('OTG camera returned no frame');
    }
    return OtgStereoFrame.fromMap(raw);
  }
}
