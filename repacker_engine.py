import os
import shutil
import struct
from pathlib import Path

import zlib
import zstandard as zstd

try:
    from pak_parser import TencentPakFile, PakCrypto
    import const
    from sm4_variant import SM4
except Exception as e:
    raise SystemExit("HATA: Gerekli sınıflar pak_parser.py'den import edilemedi.") from e

ZSTD_LEVELS = [3, 6, 9, 12, 15, 19, 22]
ZLIB_LEVELS = [6, 9]

def build_index_maps(pak):
    full_map = {}
    name_map = {}
    for dir_path, entries in pak._index.items():
        for fname, entry in entries.items():
            full = Path(dir_path) / fname
            full_map[full] = (dir_path, fname, entry)
            name_map.setdefault(fname, []).append(full)
    return full_map, name_map

def try_compress_block(raw_block: bytes, method: int, dict_obj):
    if method == const.CM_NONE:
        return raw_block
    if method == const.CM_ZLIB:
        best = None
        for lvl in ZLIB_LEVELS:
            try:
                c = zlib.compress(raw_block, lvl)
                if best is None or len(c) < len(best):
                    best = c
            except Exception:
                continue
        return best
    if method in (const.CM_ZSTD, const.CM_ZSTD_DICT):
        best = None
        for lvl in ZSTD_LEVELS:
            try:
                cctx = zstd.ZstdCompressor(level=lvl, dict_data=dict_obj)
                comp = cctx.compress(raw_block)
                if best is None or len(comp) < len(best):
                    best = comp
            except Exception:
                continue
        return best
    return None

def encrypt_simple1(data: bytes) -> bytes:
    return bytes(b ^ const.SIMPLE1_DECRYPT_KEY for b in data)

def encrypt_simple2(data: bytes) -> bytes:
    block = const.SIMPLE2_BLOCK_SIZE
    if len(data) % block != 0:
        data = data + b'\x00' * (block - (len(data) % block))
    initial_key, = struct.unpack('<I', const.SIMPLE2_DECRYPT_KEY)
    rolling = initial_key
    out = bytearray()
    for i in range(0, len(data), 4):
        p_word, = struct.unpack('<I', data[i:i+4])
        c_word = rolling ^ p_word
        out += struct.pack('<I', c_word)
        rolling = p_word
    return bytes(out)

def encrypt_sm4(data: bytes, file_path: Path, encryption_method: int) -> bytes:
    bl = SM4.block_length()
    if len(data) % bl != 0:
        data = data + b'\x00' * (bl - (len(data) % bl))
    key = PakCrypto._derive_sm4_key(file_path, encryption_method)
    sm4 = PakCrypto._sm4_context_for_key(key)
    if not hasattr(sm4, "encrypt"):
        raise RuntimeError("SM4 context missing 'encrypt' method.")
    out = bytearray()
    for i in range(0, len(data), bl):
        out += sm4.encrypt(data[i:i+bl])
    return bytes(out)

def write_cipher_to_blocks(pak_bytes: bytearray, entry, ciphertext: bytes, encryption_method: int) -> bool:
    if not entry.compressed_blocks:
        start = int(entry.offset)
        cap = int(entry.size)
        if len(ciphertext) > cap:
            return False
        pak_bytes[start:start+len(ciphertext)] = ciphertext
        if len(ciphertext) < cap:
            pak_bytes[start+len(ciphertext):start+cap] = b'\x00' * (cap - len(ciphertext))
        return True

    n = len(entry.compressed_blocks)
    indices = PakCrypto.generate_block_indices(n, encryption_method)
    total_capacity = sum(int(b.end - b.start) for b in entry.compressed_blocks)
    if len(ciphertext) > total_capacity:
        return False
    cursor = 0
    for idx in indices:
        b = entry.compressed_blocks[idx]
        start = int(b.start)
        blen = int(b.end - b.start)
        chunk = ciphertext[cursor:cursor+blen]
        if len(chunk) < blen:
            chunk = chunk + b'\x00' * (blen - len(chunk))
        pak_bytes[start:start+blen] = chunk
        cursor += blen
        if cursor >= len(ciphertext):
            break
    return True

def repack_pak(original_pak_path: Path, edited_files_paths: list, output_pak_path: Path):
    """
    Ana Rpack fonksiyonu. Gerekli parametreleri alır ve yeni PAK dosyasını oluşturur.
    """
    pak = TencentPakFile(original_pak_path)
    full_map, name_map = build_index_maps(pak)
    dict_obj = getattr(pak, "_zstd_dict", None)

    # Web arayüzünden gelen dosyalar her zaman "filename-only" modunda eşleştirilir.
    replacements = {}
    for src_path_str in edited_files_paths:
        src_path = Path(src_path_str)
        name = src_path.name
        matches = name_map.get(name, [])
        if len(matches) == 1:
            replacements[matches[0]] = src_path

    if not replacements:
        raise ValueError("Değiştirilen dosyalardan hiçbiri orijinal PAK dosyasındaki bir kayıtla eşleşmedi.")

    shutil.copy2(original_pak_path, output_pak_path)
    pak_bytes = bytearray(output_pak_path.read_bytes())
    stats = {"replaced": 0, "skipped_size": 0, "errors": 0}

    for full_in_pak, src in replacements.items():
        _, _, entry = full_map[full_in_pak]
        raw = src.read_bytes()

        uncompressed_block_size = int(entry.compression_block_size) if entry.compression_block_size > 0 else int(entry.uncompressed_size)
        blocks = [raw[i:i + uncompressed_block_size] for i in range(0, len(raw), uncompressed_block_size)] if uncompressed_block_size > 0 else [raw]

        cipher_segments, failed = [], False
        for block_raw in blocks:
            best_comp = try_compress_block(block_raw, entry.compression_method, dict_obj)
            if best_comp is None:
                failed = True; break

            aligned_len = PakCrypto.align_encrypted_content_size(len(best_comp), entry.encryption_method)
            payload = best_comp + b'\x00' * (aligned_len - len(best_comp))

            if entry.encrypted:
                em = entry.encryption_method
                if PakCrypto._is_simple1_method(em): ciphertext = encrypt_simple1(payload)
                elif PakCrypto._is_simple2_method(em): ciphertext = encrypt_simple2(payload)
                elif PakCrypto._is_sm4_method(em): ciphertext = encrypt_sm4(payload, Path(full_in_pak), em)
                else: failed = True; break
            else:
                ciphertext = payload
            cipher_segments.append(ciphertext)

        if failed:
            stats["errors"] += 1; continue

        combined = b"".join(cipher_segments)
        if not write_cipher_to_blocks(pak_bytes, entry, combined, entry.encryption_method):
            stats["skipped_size"] += 1; continue

        stats["replaced"] += 1

    output_pak_path.write_bytes(bytes(pak_bytes))
    return stats