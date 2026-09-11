"""Tests for encryption verification."""

import os
import tempfile
import pytest
from recall import DiskBackend


class TestEncryptionVerification:
    """Verify that encryption actually works correctly."""
    
    def test_encrypted_data_is_unreadable_without_key(self):
        """Verify encrypted data cannot be read without the key."""
        tmpdir = tempfile.mkdtemp()
        backend = DiskBackend(tmpdir, encryption_key="my-secret-key")
        
        backend.set("secret-key", "super-secret-data", ttl=60)
        
        # Read raw file
        files = [f for f in os.listdir(tmpdir) if f.endswith(".cache")]
        assert len(files) == 1
        
        with open(os.path.join(tmpdir, files[0]), "rb") as f:
            raw = f.read()
        
        # Should not contain plaintext
        assert b"super-secret-data" not in raw
        assert b"secret-key" not in raw
    
    def test_wrong_key_cannot_decrypt(self):
        """Verify wrong key cannot decrypt data."""
        tmpdir = tempfile.mkdtemp()
        backend1 = DiskBackend(tmpdir, encryption_key="correct-key")
        backend1.set("key1", "sensitive-data", ttl=60)
        
        # Different backend with wrong key
        backend2 = DiskBackend(tmpdir, encryption_key="wrong-key")
        result = backend2.get("key1")
        
        assert result is None
    
    def test_correct_key_can_decrypt(self):
        """Verify correct key can decrypt data."""
        tmpdir = tempfile.mkdtemp()
        backend = DiskBackend(tmpdir, encryption_key="my-key")
        
        backend.set("key1", "sensitive-data", ttl=60)
        result = backend.get("key1")
        
        assert result is not None
        assert result[1] == "sensitive-data"
    
    def test_different_nonces_each_encryption(self):
        """Verify each encryption uses a different nonce."""
        tmpdir = tempfile.mkdtemp()
        backend = DiskBackend(tmpdir, encryption_key="my-key")
        
        backend.set("key1", "data", ttl=60)
        backend.set("key2", "data", ttl=60)
        
        files = [f for f in os.listdir(tmpdir) if f.endswith(".cache")]
        assert len(files) == 2
        
        # Read raw data
        with open(os.path.join(tmpdir, files[0]), "rb") as f:
            raw1 = f.read()
        with open(os.path.join(tmpdir, files[1]), "rb") as f:
            raw2 = f.read()
        
        # First 12 bytes are nonce - should be different
        assert raw1[:12] != raw2[:12]
    
    def test_no_encryption_when_key_is_none(self):
        """Verify no encryption when key is None."""
        tmpdir = tempfile.mkdtemp()
        backend = DiskBackend(tmpdir, encryption_key=None)
        
        backend.set("key1", "plain-data", ttl=60)
        
        files = [f for f in os.listdir(tmpdir) if f.endswith(".cache")]
        with open(os.path.join(tmpdir, files[0]), "rb") as f:
            raw = f.read()
        
        # Should contain plaintext
        assert b"plain-data" in raw
    
    def test_encryption_with_various_data_types(self):
        """Verify encryption works with various data types."""
        tmpdir = tempfile.mkdtemp()
        backend = DiskBackend(tmpdir, encryption_key="my-key")
        
        test_data = [
            ("string", "hello world"),
            ("integer", 42),
            ("float", 3.14),
            ("list", [1, 2, 3]),
            ("dict", {"a": 1, "b": 2}),
            ("none", None),
            ("tuple", (1, 2, 3)),
        ]
        
        for key, value in test_data:
            backend.set(key, value, ttl=60)
            result = backend.get(key)
            assert result is not None
            assert result[1] == value
    
    # Note: Key rotation test is in test_recall.py::TestDiskEncryption::test_key_rotation
