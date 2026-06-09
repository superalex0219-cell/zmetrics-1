"""Local stereo capture (ZED 2 as a UVC camera).

ZED 2 enumerates as a standard UVC webcam emitting a side-by-side (left|right) frame.
The ZED SDK is not required while CV runs server-side — we grab the raw frame, split it
into left/right, and upload both. See ``stereo.split_side_by_side``.
"""
