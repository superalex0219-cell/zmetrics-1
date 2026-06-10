package com.zmetrics.zmetrics_mobile

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.hardware.camera2.CameraAccessException
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.usb.UsbManager
import android.media.Image
import android.media.ImageReader
import android.os.Handler
import android.os.HandlerThread
import android.util.Size
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.ByteArrayOutputStream
import java.util.concurrent.atomic.AtomicBoolean

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "zmetrics/otg_stereo_camera",
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "listUsbCameras" -> result.success(listUsbCameras())
                "captureStereoFrame" -> {
                    val splitSideBySide =
                        call.argument<Boolean>("splitSideBySide") ?: true
                    captureStereoFrame(splitSideBySide, result)
                }
                else -> result.notImplemented()
            }
        }
    }

    private fun listUsbCameras(): List<Map<String, Any?>> {
        val usb = getSystemService(Context.USB_SERVICE) as UsbManager
        return usb.deviceList.values.map { device ->
            mapOf(
                "deviceName" to device.deviceName,
                "manufacturerName" to device.manufacturerName,
                "productName" to device.productName,
                "vendorId" to device.vendorId,
                "productId" to device.productId,
                "deviceClass" to device.deviceClass,
                "deviceSubclass" to device.deviceSubclass,
                "hasPermission" to usb.hasPermission(device),
            )
        }
    }

    private fun captureStereoFrame(
        splitSideBySide: Boolean,
        result: MethodChannel.Result,
    ) {
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.CAMERA), CAMERA_PERMISSION_REQUEST)
            result.error(
                "CAMERA_PERMISSION",
                "Camera permission requested; repeat capture after granting it",
                null,
            )
            return
        }

        val manager = getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val cameraId = findExternalCameraId(manager)
        if (cameraId == null) {
            result.error(
                "NO_EXTERNAL_CAMERA",
                "Android Camera2 did not expose an OTG/external camera",
                null,
            )
            return
        }

        val stream = chooseCaptureStream(manager, cameraId)
        if (stream == null) {
            result.error(
                "NO_CAPTURE_STREAM",
                "External camera does not expose a JPEG or YUV capture stream",
                null,
            )
            return
        }

        openAndCapture(manager, cameraId, stream, splitSideBySide, result)
    }

    private fun findExternalCameraId(manager: CameraManager): String? {
        return try {
            manager.cameraIdList.firstOrNull { id ->
                val lensFacing = manager
                    .getCameraCharacteristics(id)
                    .get(CameraCharacteristics.LENS_FACING)
                lensFacing == CameraCharacteristics.LENS_FACING_EXTERNAL
            }
        } catch (_: CameraAccessException) {
            null
        }
    }

    private fun chooseCaptureStream(manager: CameraManager, cameraId: String): CaptureStream? {
        return try {
            val map = manager
                .getCameraCharacteristics(cameraId)
                .get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
                ?: return null
            choosePracticalSize(map.getOutputSizes(ImageFormat.JPEG))?.let {
                return CaptureStream(it, ImageFormat.JPEG)
            }
            choosePracticalSize(map.getOutputSizes(ImageFormat.YUV_420_888))?.let {
                return CaptureStream(it, ImageFormat.YUV_420_888)
            }
            null
        } catch (_: CameraAccessException) {
            null
        }
    }

    private fun choosePracticalSize(sizes: Array<Size>?): Size? {
        if (sizes.isNullOrEmpty()) return null
        val practical = sizes.filter { it.width <= 2560 && it.height <= 1440 }
        return (practical.ifEmpty { sizes.toList() }).maxByOrNull {
            it.width.toLong() * it.height.toLong()
        }
    }

    @SuppressLint("MissingPermission")
    private fun openAndCapture(
        manager: CameraManager,
        cameraId: String,
        stream: CaptureStream,
        splitSideBySide: Boolean,
        result: MethodChannel.Result,
    ) {
        val thread = HandlerThread("ZMetricsOtgCamera").apply { start() }
        val handler = Handler(thread.looper)
        val delivered = AtomicBoolean(false)
        val reader =
            ImageReader.newInstance(stream.size.width, stream.size.height, stream.format, 1)
        var camera: CameraDevice? = null
        var session: CameraCaptureSession? = null

        fun cleanup() {
            try {
                session?.close()
            } catch (_: Exception) {
            }
            try {
                camera?.close()
            } catch (_: Exception) {
            }
            try {
                reader.close()
            } catch (_: Exception) {
            }
            thread.quitSafely()
        }

        fun fail(code: String, message: String) {
            if (delivered.compareAndSet(false, true)) {
                cleanup()
                result.error(code, message, null)
            }
        }

        reader.setOnImageAvailableListener({ imageReader ->
            val image = imageReader.acquireLatestImage() ?: return@setOnImageAvailableListener
            var imageClosed = false
            try {
                val jpeg = imageToJpeg(image, stream.format)
                val payload = buildFramePayload(jpeg, splitSideBySide)
                if (delivered.compareAndSet(false, true)) {
                    image.close()
                    imageClosed = true
                    cleanup()
                    result.success(payload)
                }
            } catch (exc: Exception) {
                fail("CAPTURE_DECODE_FAILED", exc.message ?: "Could not read JPEG frame")
            } finally {
                if (!imageClosed) {
                    try {
                        image.close()
                    } catch (_: Exception) {
                    }
                }
            }
        }, handler)

        handler.postDelayed({
            fail("CAPTURE_TIMEOUT", "External camera did not return a frame in time")
        }, CAPTURE_TIMEOUT_MS)

        try {
            manager.openCamera(
                cameraId,
                object : CameraDevice.StateCallback() {
                    override fun onOpened(device: CameraDevice) {
                        camera = device
                        try {
                            device.createCaptureSession(
                                listOf(reader.surface),
                                object : CameraCaptureSession.StateCallback() {
                                    override fun onConfigured(captureSession: CameraCaptureSession) {
                                        session = captureSession
                                        try {
                                            val request = device
                                                .createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE)
                                                .apply { addTarget(reader.surface) }
                                                .build()
                                            captureSession.capture(request, null, handler)
                                        } catch (exc: Exception) {
                                            fail(
                                                "CAPTURE_REQUEST_FAILED",
                                                exc.message ?: "Could not capture a frame",
                                            )
                                        }
                                    }

                                    override fun onConfigureFailed(captureSession: CameraCaptureSession) {
                                        fail(
                                            "CAPTURE_SESSION_FAILED",
                                            "Could not configure external camera capture session",
                                        )
                                    }
                                },
                                handler,
                            )
                        } catch (exc: Exception) {
                            fail(
                                "CAMERA_SESSION_FAILED",
                                exc.message ?: "Could not open capture session",
                            )
                        }
                    }

                    override fun onDisconnected(device: CameraDevice) {
                        fail("CAMERA_DISCONNECTED", "External camera was disconnected")
                    }

                    override fun onError(device: CameraDevice, error: Int) {
                        fail("CAMERA_ERROR", "External camera error $error")
                    }
                },
                handler,
            )
        } catch (exc: Exception) {
            fail("CAMERA_OPEN_FAILED", exc.message ?: "Could not open external camera")
        }
    }

    private fun buildFramePayload(
        jpeg: ByteArray,
        splitSideBySide: Boolean,
    ): Map<String, Any?> {
        val bitmap = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.size)
            ?: return mapOf(
                "leftJpeg" to jpeg,
                "rightJpeg" to null,
                "width" to 0,
                "height" to 0,
                "sideBySide" to false,
            )

        val isSideBySide = splitSideBySide && bitmap.width.toFloat() / bitmap.height > 1.8f
        if (!isSideBySide) {
            val width = bitmap.width
            val height = bitmap.height
            bitmap.recycle()
            return mapOf(
                "leftJpeg" to jpeg,
                "rightJpeg" to null,
                "width" to width,
                "height" to height,
                "sideBySide" to false,
            )
        }

        val halfWidth = bitmap.width / 2
        val height = bitmap.height
        val left = Bitmap.createBitmap(bitmap, 0, 0, halfWidth, bitmap.height)
        val right = Bitmap.createBitmap(bitmap, halfWidth, 0, halfWidth, bitmap.height)
        val leftJpeg = compressJpeg(left)
        val rightJpeg = compressJpeg(right)
        left.recycle()
        right.recycle()
        bitmap.recycle()
        return mapOf(
            "leftJpeg" to leftJpeg,
            "rightJpeg" to rightJpeg,
            "width" to halfWidth,
            "height" to height,
            "sideBySide" to true,
        )
    }

    private fun compressJpeg(bitmap: Bitmap): ByteArray {
        val out = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)
        return out.toByteArray()
    }

    private fun imageToJpeg(image: Image, format: Int): ByteArray {
        if (format == ImageFormat.JPEG) {
            val buffer = image.planes[0].buffer
            val jpeg = ByteArray(buffer.remaining())
            buffer.get(jpeg)
            return jpeg
        }

        if (format == ImageFormat.YUV_420_888) {
            val nv21 = yuv420ToNv21(image)
            val out = ByteArrayOutputStream()
            val compressed = YuvImage(nv21, ImageFormat.NV21, image.width, image.height, null)
                .compressToJpeg(Rect(0, 0, image.width, image.height), 92, out)
            if (!compressed) {
                throw IllegalStateException("Could not compress YUV frame to JPEG")
            }
            return out.toByteArray()
        }

        throw IllegalArgumentException("Unsupported capture format $format")
    }

    private fun yuv420ToNv21(image: Image): ByteArray {
        val width = image.width
        val height = image.height
        val ySize = width * height
        val nv21 = ByteArray(ySize + (ySize / 2))
        val yPlane = image.planes[0]
        val uPlane = image.planes[1]
        val vPlane = image.planes[2]
        val yBuffer = yPlane.buffer
        val uBuffer = uPlane.buffer
        val vBuffer = vPlane.buffer

        var output = 0
        for (row in 0 until height) {
            val rowOffset = row * yPlane.rowStride
            for (col in 0 until width) {
                nv21[output++] = yBuffer.get(rowOffset + col * yPlane.pixelStride)
            }
        }

        output = ySize
        for (row in 0 until height / 2) {
            val uRowOffset = row * uPlane.rowStride
            val vRowOffset = row * vPlane.rowStride
            for (col in 0 until width / 2) {
                nv21[output++] = vBuffer.get(vRowOffset + col * vPlane.pixelStride)
                nv21[output++] = uBuffer.get(uRowOffset + col * uPlane.pixelStride)
            }
        }

        return nv21
    }

    private data class CaptureStream(
        val size: Size,
        val format: Int,
    )

    companion object {
        private const val CAMERA_PERMISSION_REQUEST = 4081
        private const val CAPTURE_TIMEOUT_MS = 10_000L
    }
}
