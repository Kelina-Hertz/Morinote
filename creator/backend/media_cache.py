"""Small, disposable image previews using Windows' bundled image decoder."""
import ctypes
import hashlib
import os
from pathlib import Path
import threading
import uuid

_workers = threading.Semaphore(2)
_created = 0
_png_encoder = bytes.fromhex('06f47c55041ad3119a730000f81ef32e')


def thumbnail(source, cache, size, stamp):
    if os.name != 'nt' or source.suffix.lower() not in {'.png', '.jpg', '.jpeg'}:
        return source
    key = hashlib.sha256((str(source) + repr(stamp) + str(size)).encode()).hexdigest()
    target = cache / (key + '.png')
    with _workers:
        if target.is_file():
            return target
        cache.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(key + '.' + uuid.uuid4().hex + '.tmp')
        try:
            _resize(source, temp, size)
            # Do not cache a preview if an external editor changed its source.
            stat = source.stat()
            if (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size) != stamp:
                return source
            os.replace(temp, target)
            # Bound disposable disk data, including previews from old versions.
            global _created
            _created += 1
            if _created % 32:
                return target
            items = sorted(cache.glob('*.png'), key=lambda p: p.stat().st_mtime_ns, reverse=True)
            total = 0
            for i, item in enumerate(items):
                total += item.stat().st_size
                if i >= 512 or total > 64 * 1024 * 1024:
                    item.unlink(missing_ok=True)
            return target
        except (OSError, ValueError):
            return source
        finally:
            temp.unlink(missing_ok=True)


def _resize(source, target, size):
    from ctypes import wintypes as w
    class Startup(ctypes.Structure):
        _fields_ = [('version', w.UINT), ('callback', ctypes.c_void_p), ('background', w.BOOL), ('codecs', w.BOOL)]
    dll = ctypes.WinDLL('gdiplus')
    ptr = ctypes.c_void_p
    specs = {
        'GdiplusStartup': [ctypes.POINTER(ptr), ctypes.POINTER(Startup), ptr],
        'GdiplusShutdown': [ptr],
        'GdipCreateBitmapFromFile': [w.LPCWSTR, ctypes.POINTER(ptr)],
        'GdipGetImageWidth': [ptr, ctypes.POINTER(w.UINT)],
        'GdipGetImageHeight': [ptr, ctypes.POINTER(w.UINT)],
        'GdipGetImageThumbnail': [ptr, w.UINT, w.UINT, ctypes.POINTER(ptr), ptr, ptr],
        'GdipSaveImageToFile': [ptr, w.LPCWSTR, ptr, ptr],
        'GdipDisposeImage': [ptr],
    }
    for name, args in specs.items():
        getattr(dll, name).argtypes = args
    def check(status):
        if status:
            raise ValueError('缩略图解码失败。')
    token, image, small = ptr(), ptr(), ptr()
    check(dll.GdiplusStartup(ctypes.byref(token), ctypes.byref(Startup(1, None, False, False)), None))
    try:
        check(dll.GdipCreateBitmapFromFile(str(source), ctypes.byref(image)))
        width, height = w.UINT(), w.UINT()
        check(dll.GdipGetImageWidth(image, ctypes.byref(width)))
        check(dll.GdipGetImageHeight(image, ctypes.byref(height)))
        ratio = min(1, size / max(width.value, height.value, 1))
        check(dll.GdipGetImageThumbnail(image, max(1, int(width.value * ratio)), max(1, int(height.value * ratio)), ctypes.byref(small), None, None))
        encoder = ctypes.create_string_buffer(_png_encoder)
        check(dll.GdipSaveImageToFile(small, str(target), encoder, None))
    finally:
        if small: dll.GdipDisposeImage(small)
        if image: dll.GdipDisposeImage(image)
        dll.GdiplusShutdown(token)
