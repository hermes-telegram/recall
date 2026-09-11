"""Compression algorithms for recall-cache."""

import zlib
from typing import Any


class Compressor:
    """Compression backend with multiple algorithms."""
    
    @staticmethod
    def compress(data: bytes, algorithm: str = "zlib", level: int = 6) -> bytes:
        """Compress data with specified algorithm."""
        if algorithm == "zlib":
            return zlib.compress(data, level)
        elif algorithm == "lz4":
            try:
                import lz4.frame
                return lz4.frame.compress(data, compression_level=level)
            except ImportError:
                return zlib.compress(data, level)
        elif algorithm == "zstd":
            try:
                import zstandard as zstd
                cctx = zstd.ZstdCompressor(level=level)
                return cctx.compress(data)
            except ImportError:
                return zlib.compress(data, level)
        else:
            return zlib.compress(data, level)
    
    @staticmethod
    def decompress(data: bytes, algorithm: str = "zlib") -> bytes:
        """Decompress data with specified algorithm."""
        if algorithm == "zlib":
            return zlib.decompress(data)
        elif algorithm == "lz4":
            try:
                import lz4.frame
                return lz4.frame.decompress(data)
            except ImportError:
                return zlib.decompress(data)
        elif algorithm == "zstd":
            try:
                import zstandard as zstd
                dctx = zstd.ZstdDecompressor()
                return dctx.decompress(data)
            except ImportError:
                return zlib.decompress(data)
        else:
            return zlib.decompress(data)
