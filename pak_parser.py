# Gerekli Kütüphaneler
import itertools as it
import math
import struct
import zlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import PurePath, Path
import shutil
import os

# Projenizin Orijinal Kütüphaneleri
import gmalg
from Crypto.Cipher import AES
from Crypto.Cipher.AES import MODE_CBC
from Crypto.Hash import SHA1
from Crypto.Util.Padding import unpad
from zstandard import ZstdDecompressor, ZstdCompressionDict, DICT_TYPE_AUTO

# Yerel Dosyalarınızdan Gelen Importlar
import const
from sm4_variant import SM4

# =============================================================================
# BÖLÜM 1: ORİJİNAL PAK DOSYASI İŞLEME MANTIĞI
# =============================================================================

class Misc:
    @staticmethod
    def pad_to_n(data: bytes, n: int) -> bytes:
        assert n > 0
        padding = n - (len(data) % n)
        if padding == n:
            return data
        return data + b'\x00' * padding

    @staticmethod
    def align_up(x: int, n: int) -> int:
        return ((x + n - 1) // n) * n


class Reader:
    def __init__(self, buffer, cursor=0):
        self._buffer = buffer
        self._cursor = cursor

    def u1(self, move_cursor=True) -> int:
        return self.unpack('B', move_cursor=move_cursor)[0]

    def u4(self, move_cursor=True) -> int:
        return self.unpack('<I', move_cursor=move_cursor)[0]

    def u8(self, move_cursor=True) -> int:
        return self.unpack('<Q', move_cursor=move_cursor)[0]

    def i1(self, move_cursor=True) -> int:
        return self.unpack('b', move_cursor=move_cursor)[0]

    def i4(self, move_cursor=True) -> int:
        return self.unpack('<i', move_cursor=move_cursor)[0]

    def i8(self, move_cursor=True) -> int:
        return self.unpack('<q', move_cursor=move_cursor)[0]

    def s(self, n: int, move_cursor=True) -> bytes:
        return self.unpack(f'{n}s', move_cursor=move_cursor)[0]

    def unpack(self, f: str | bytes, offset=0, move_cursor=True):
        x = struct.unpack_from(f, self._buffer, self._cursor + offset)
        if move_cursor:
            self._cursor += struct.calcsize(f)
        return x

    def string(self, move_cursor=True) -> str:
        length = self.i4(move_cursor=move_cursor)
        if length == 0:
            return str()
        assert length > 0
        offset = 0 if move_cursor else 4
        return self.unpack(f'{length}s', offset=offset, move_cursor=move_cursor)[0].rstrip(b'\x00').decode()


class PakInfo:
    def __init__(self, buffer, keystream: list[int]):
        def decrypt_index_encrypted(x: int) -> int:
            MASK_8 = 0xFF
            return (x ^ keystream[3]) & MASK_8

        def decrypt_magic(x: int) -> int:
            return x ^ keystream[2]

        def decrypt_index_hash(x: bytes) -> bytes:
            key = struct.pack('<5I', *keystream[4:][:5])
            assert len(x) == len(key)
            return bytes(a ^ b for a, b in zip(x, key))

        def decrypt_index_size(x: int) -> int:
            return x ^ ((keystream[10] << 32) | keystream[11])

        def decrypt_index_offset(x: int) -> int:
            return x ^ ((keystream[0] << 32) | keystream[1])

        reader = Reader(buffer[-PakInfo._mem_size(-1):])

        self.index_encrypted: bool = decrypt_index_encrypted(reader.u1()) == 1
        self.magic: int = decrypt_magic(reader.u4())
        self.version: int = reader.u4()
        self.index_hash: bytes = decrypt_index_hash(reader.s(20)) if self.version >= 6 else bytes()
        self.index_size: int = decrypt_index_size(reader.u8())
        self.index_offset: int = decrypt_index_offset(reader.u8())
        if self.version <= 3:
            self.index_encrypted = False

    @staticmethod
    def _mem_size(_: int) -> int:
        return 1 + 4 + 4 + 20 + 8 + 8


class TencentPakInfo(PakInfo):
    def __init__(self, buffer, keystream: list[int]):
        def decrypt_unk(x: bytes) -> bytes:
            key = struct.pack('<8I', *keystream[7:][:8])
            assert len(x) == len(key)
            return bytes(a ^ b for a, b in zip(x, key))

        def decrypt_stem_hash(x: int) -> int:
            return x ^ keystream[8]

        def decrypt_unk_hash(x: int) -> int:
            return x ^ keystream[9]

        super().__init__(buffer, keystream)

        reader = Reader(buffer[-TencentPakInfo._mem_size(self.version):])

        self.unk1: bytes = decrypt_unk(reader.s(32)) if self.version >= 7 else bytes()
        self.packed_key: bytes = reader.s(256) if self.version >= 8 else bytes()
        self.packed_iv: bytes = reader.s(256) if self.version >= 8 else bytes()
        self.packed_index_hash: bytes = reader.s(256) if self.version >= 8 else bytes()
        self.stem_hash: int = decrypt_stem_hash(reader.u4()) if self.version >= 9 else 0
        self.unk2: int = decrypt_unk_hash(reader.u4()) if self.version >= 9 else 0
        self.content_org_hash: bytes = reader.s(20) if self.version >= 12 else bytes()

    @staticmethod
    def _mem_size(version: int) -> int:
        size_for_7 = 32 if version >= 7 else 0
        size_for_8 = 256 * 3 if version >= 8 else 0
        size_for_9 = 4 * 2 if version >= 9 else 0
        size_for_12 = 20 if version >= 12 else 0
        return PakInfo._mem_size(version) + size_for_7 + size_for_8 + size_for_9 + size_for_12


class PakCompressedBlock:
    def __init__(self, reader: Reader):
        self.start: int = reader.u8()
        self.end: int = reader.u8()


@dataclass
class TencentPakEntry:
    def __init__(self, reader: Reader, version: int):
        self.content_hash: bytes = reader.s(20)
        if version <= 1:
            _ = reader.u8()
        self.offset: int = reader.u8()
        self.uncompressed_size: int = reader.u8()
        self.compression_method: int = reader.u4() & const.CM_MASK
        self.size: int = reader.u8()
        self.unk1: int = reader.u1() if version >= 5 else 0
        self.unk2: bytes = reader.s(20) if version >= 5 else bytes()
        self.compressed_blocks: list[PakCompressedBlock] = [PakCompressedBlock(reader) for _ in range(
            reader.u4())] if self.compression_method != 0 and version >= 3 else []
        self.compression_block_size: int = reader.u4() if version >= 4 else 0
        self.encrypted: bool = reader.u1() == 1 if version >= 4 else False
        
        # --- DEĞİŞİKLİK BURADA BAŞLIYOR ---
        self.encryption_method: int = reader.u4() if version >= 12 else 0
        # Yeni eklenen alan:
        self.index_new_sep: int = reader.u4() if version >= 12 else 0
        # --- DEĞİŞİKLİK SONA ERDİ ---

    def _mem_size(self, version: int) -> int:
        size_for_123 = 20 + 8 + 8 + 4 + 8 + (8 if version == 1 else 0)
        size_for_4 = 4 + 1 if version >= 4 else 0
        size_for_compressed_blocks = 4 + len(self.compressed_blocks) * 16 if self.compressed_blocks else 0
        size_for_5 = 1 + 20 if version >= 5 else 0
        size_for_12 = 4 if version >= 12 else 0
        return size_for_123 + size_for_4 + size_for_5 + size_for_12 + size_for_compressed_blocks


class PakCrypto:
    class _LCG:
        def __init__(self, seed: int):
            self.state = seed

        def next(self) -> int:
            MASK_32 = 0xFFFFFFFF
            MSB_1 = 1 << 31

            def wrap(x: int) -> int:
                x &= MASK_32
                if not x & MSB_1:
                    return x
                else:
                    return ((x + MSB_1) & MASK_32) - MSB_1

            x1 = wrap(0x41C64E6D * self.state)
            self.state = wrap(x1 + 12345)
            x2 = wrap(x1 + 0x13038) if self.state < 0 else self.state
            return ((x2 >> 16) & MASK_32) % 0x7FFF

    @staticmethod
    def zuc_keystream() -> list[int]:
        zuc = gmalg.ZUC(const.ZUC_KEY, const.ZUC_IV)
        return [struct.unpack('>I', zuc.generate())[0] for _ in range(16)]

    @staticmethod
    def _xorxor(buffer, x) -> bytes:
        return bytes(buffer[i] ^ x[i % len(x)] for i in range(len(buffer)))

    @staticmethod
    def _hashhash(buffer, n: int) -> bytes:
        result = bytes()
        for i in range(math.ceil(n / SHA1.digest_size)):
            result += SHA1.new(buffer).digest()
        if len(result) >= n:
            result = result[:n]
        else:
            result += b'\x00' * (n - len(result))
        return result

    @staticmethod
    def _meowmeow(buffer) -> bytes:
        def unpad(x):
            skip = 1 + next((i for i in range(len(x)) if x[i] != 0))
            return x[skip:]

        if len(buffer) < 43:
            return bytes()

        x1 = buffer[1:][:SHA1.digest_size]
        x2 = buffer[SHA1.digest_size + 1:]
        x1 = PakCrypto._xorxor(x1, PakCrypto._hashhash(x2, len(x1)))
        x2 = PakCrypto._xorxor(x2, PakCrypto._hashhash(x1, len(x2)))

        part1, m = (x2[:SHA1.digest_size], x2[SHA1.digest_size:])
        if part1 != SHA1.new(b'\x00' * SHA1.digest_size).digest():
            return bytes()

        return unpad(m)

    @staticmethod
    def rsa_extract(signature: bytes, modulus: bytes) -> bytes:
        c = int.from_bytes(signature, 'little')
        n = int.from_bytes(modulus, 'little')
        e = 0x10001
        m = pow(c, e, n).to_bytes(256, 'little').rstrip(b'\x00')
        return PakCrypto._meowmeow(Misc.pad_to_n(m, 4))

    @staticmethod
    def _decrypt_simple1(ciphertext) -> bytes:
        return bytes(x ^ const.SIMPLE1_DECRYPT_KEY for x in ciphertext)

    @staticmethod
    def _decrypt_simple2(ciphertext) -> bytes:
        class RollingKey:
            def __init__(self, initial_value: int):
                self._value = initial_value

            def update(self, x: int) -> int:
                self._value ^= x
                return self._value

        assert len(ciphertext) % const.SIMPLE2_BLOCK_SIZE == 0

        initial_key, = struct.unpack('<I', const.SIMPLE2_DECRYPT_KEY)
        rolling_key = RollingKey(initial_key)
        plaintext = (
            struct.pack('<I', rolling_key.update(x)) for x in struct.unpack(f'<{len(ciphertext) // 4}I', ciphertext)
        )
        return bytes(it.chain.from_iterable(plaintext))

    @staticmethod
    @lru_cache(maxsize=1)
    def _derive_sm4_key(file_path: PurePath, encryption_method: int) -> bytes:
        part1 = file_path.stem.lower()
        if encryption_method == const.EM_SM4_2:
            secret = const.SM4_SECRET_2
        elif encryption_method == const.EM_SM4_4:
            secret = const.SM4_SECRET_4
        else:
            index = (encryption_method - const.EM_SM4_NEW_BASE) % len(const.SM4_SECRET_NEW)
            secret = f'{const.SM4_SECRET_NEW[index]}{encryption_method}'
        return SHA1.new(str(part1 + secret).encode()).digest()[:SM4.key_length()]

    @staticmethod
    @lru_cache(maxsize=1)
    def _sm4_context_for_key(key: bytes) -> SM4:
        return SM4(key)

    @staticmethod
    def _decrypt_sm4(ciphertext, file_path: PurePath, encryption_method: int) -> bytes:
        assert len(ciphertext) % SM4.block_length() == 0

        key = PakCrypto._derive_sm4_key(file_path, encryption_method)
        sm4 = PakCrypto._sm4_context_for_key(key)
        return bytes(
            it.chain.from_iterable(
                sm4.decrypt(x) for x in it.batched(ciphertext, SM4.block_length())
            )
        )

    @staticmethod
    def decrypt_index(ciphertext, pak_info: TencentPakInfo) -> bytes:
        if pak_info.version > 7:
            key = PakCrypto.rsa_extract(pak_info.packed_key, const.RSA_MOD_1)
            iv = PakCrypto.rsa_extract(pak_info.packed_iv, const.RSA_MOD_1)
            assert len(key) == 32 and len(iv) == 32

            aes = AES.new(key, MODE_CBC, iv[:16])
            return unpad(aes.decrypt(ciphertext), AES.block_size)
        else:
            return bytes(PakCrypto._decrypt_simple1(ciphertext))

    @staticmethod
    def _is_simple1_method(encryption_method: int) -> bool:
        return encryption_method == const.EM_SIMPLE1

    @staticmethod
    def _is_simple2_method(encryption_method: int) -> bool:
        return encryption_method == const.EM_SIMPLE2

    @staticmethod
    def _is_sm4_method(encryption_method: int) -> bool:
        return (encryption_method == const.EM_SM4_2
                or encryption_method == const.EM_SM4_4
                or encryption_method & const.EM_SM4_NEW_MASK != 0)

    @staticmethod
    def align_encrypted_content_size(n: int, encryption_method: int) -> int:
        if PakCrypto._is_simple2_method(encryption_method):
            return Misc.align_up(n, const.SIMPLE2_BLOCK_SIZE)
        elif PakCrypto._is_sm4_method(encryption_method):
            return Misc.align_up(n, SM4.block_length())
        else:
            return n

    @staticmethod
    def decrypt_block(ciphertext, file: PurePath, encryption_method: int) -> bytes:
        if PakCrypto._is_simple1_method(encryption_method):
            return PakCrypto._decrypt_simple1(ciphertext)
        elif PakCrypto._is_simple2_method(encryption_method):
            return PakCrypto._decrypt_simple2(ciphertext)
        elif PakCrypto._is_sm4_method(encryption_method):
            return PakCrypto._decrypt_sm4(ciphertext, file, encryption_method)
        else:
            assert False, f"Bilinmeyen şifreleme metodu: {encryption_method}"

    @staticmethod
    @lru_cache(maxsize=33)
    def generate_block_indices(n: int, encryption_method: int) -> list[int]:
        if not PakCrypto._is_sm4_method(encryption_method):
            return list(range(n))

        permutation = []
        lcg = PakCrypto._LCG(n)
        while len(permutation) != n:
            x = lcg.next() % n
            if x not in permutation:
                permutation.append(x)

        inverse = [0] * len(permutation)
        for i, x in enumerate(permutation):
            inverse[x] = i

        return inverse

    @staticmethod
    def stat():
        print(PakCrypto._derive_sm4_key.cache_info())
        print(PakCrypto._sm4_context_for_key.cache_info())


class PakCompression:
    @staticmethod
    @lru_cache(maxsize=33)
    def _zstd_decompressor(dict: ZstdCompressionDict) -> ZstdDecompressor:
        return ZstdDecompressor(dict)

    @staticmethod
    def zstd_dictionary(dict_data) -> ZstdCompressionDict:
        return ZstdCompressionDict(dict_data, DICT_TYPE_AUTO)

    @staticmethod
    def decompress_block(block, dict: ZstdCompressionDict | None, compression_method: int) -> bytes:
        if compression_method == const.CM_ZLIB:
            return zlib.decompress(block)
        elif compression_method == const.CM_ZSTD or compression_method == const.CM_ZSTD_DICT:
            if compression_method != const.CM_ZSTD_DICT:
                dict = None
            return PakCompression._zstd_decompressor(dict).decompress(block)
        else:
            assert False, f"Bilinmeyen sıkıştırma metodu: {compression_method}"


class TencentPakFile:
    def __init__(self, file_path: PurePath, is_od=False):
        self._file_path = file_path
        with open(file_path, 'rb') as file:
            self._file_content = memoryview(file.read())
        self._is_od = is_od
        self._mount_point = PurePath()
        self._is_zstd_with_dict = 'zsdic' in str(self._file_path)
        self._zstd_dict = None
        self._files: list[TencentPakEntry] = []
        self._index: dict[PurePath, dict[str, TencentPakEntry]] = {}
        self._pak_info = TencentPakInfo(self._file_content, PakCrypto.zuc_keystream())

        self._verify_stem_hash()
        self._tencent_load_index()

    def _verify_stem_hash(self) -> None:
        if not self._is_od and self._pak_info.version >= 9:
            assert self._pak_info.stem_hash == zlib.crc32(self._file_path.stem.encode('utf-32le'))
            pass

    def _tencent_load_index(self) -> None:
        index_data = self._file_content[self._pak_info.index_offset:][:self._pak_info.index_size]

        if self._pak_info.index_encrypted:
            index_data = PakCrypto.decrypt_index(index_data, self._pak_info)
        else:
            index_data = bytes(index_data)

        self._verify_index_hash(index_data)
        self._load_index(index_data)

    def _verify_index_hash(self, index_data) -> None:
        expected_hash = self._pak_info.index_hash
        if not self._is_od and self._pak_info.version >= 6:
            if self._pak_info.version >= 8:
                assert expected_hash == PakCrypto.rsa_extract(self._pak_info.packed_index_hash, const.RSA_MOD_2)
            assert expected_hash == SHA1.new(index_data).digest()

    @staticmethod
    def _construct_mount_point(mount_point: str) -> PurePath:
        result = PurePath()
        for part in PurePath(mount_point).parts:
            if part != '..':
                result /= part
        return result

    def _peek_content(self, offset: int, size: int, encryption_method: int) -> memoryview:
        size = PakCrypto.align_encrypted_content_size(size, encryption_method)
        return self._file_content[offset:][:size]

    def _peek_block_content(self, block: PakCompressedBlock, encryption_method: int) -> memoryview:
        size = PakCrypto.align_encrypted_content_size(block.end - block.start, encryption_method)
        return self._file_content[block.start:][:size]

    def _construct_zstd_dict(self, dict_entry: TencentPakEntry) -> None:
        assert not self._zstd_dict
        assert not dict_entry.encrypted
        assert dict_entry.compression_method == const.CM_NONE

        reader = Reader(self._peek_content(dict_entry.offset, dict_entry.size, 0))

        dict_size = reader.u8()
        _ = reader.u4()
        assert dict_size == reader.u4()
        dict_data = reader.s(dict_size)
        self._zstd_dict = PakCompression.zstd_dictionary(dict_data)

    def _load_index(self, index_data) -> None:
        if self._pak_info.version <= 10:
            assert False, f"Pak sürümü {self._pak_info.version} desteklenmiyor (sadece > 10)."

        reader = Reader(index_data)

        self._mount_point = self._construct_mount_point(reader.string())

        file_count = reader.u4()
        self._files = [TencentPakEntry(reader, self._pak_info.version) for _ in range(file_count)]

        dir_count = reader.u8()
        for _ in range(dir_count):
            dir_path = PurePath(reader.string())

            files_in_dir_count = reader.u8()
            e = {reader.string(): self._files[~reader.i4()] for _ in range(files_in_dir_count)}

            if self._is_zstd_with_dict and dir_path.name == 'zstddic':
                assert len(e) == 1
                self._construct_zstd_dict(e[[*e.keys()][0]])
                continue
            self._index.update({PurePath(dir_path): e})

    def _write_to_disk(self, file_path: Path, entry: TencentPakEntry) -> None:
        """
        Dosya verisini diske yazar. Yazmadan önce dosyanın bulunacağı klasör yapısının
        var olduğundan emin olur.
        """
        encryption_method = entry.encryption_method
        compression_method = entry.compression_method

        try:
            # YENİ VE KRİTİK ADIM: Dosyayı yazmadan hemen önce üst klasörünü oluştur.
            # file_path.parent -> dosyanın tam yolundaki klasör kısmını alır (örn: C:/results/klasor/)
            # .mkdir() -> bu klasörü oluşturur.
            # parents=True -> Eğer iç içe birden fazla klasör yoksa (örn: a/b/c), hepsini oluşturur.
            # exist_ok=True -> Eğer klasör zaten varsa hata vermeden devam etmesini sağlar.
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'wb') as file:
                # Geri kalan kod aynı, sıkıştırma ve şifre çözme mantığı değişmiyor.
                if compression_method == const.CM_NONE:
                    data = self._peek_content(entry.offset, entry.size, encryption_method)
                    if entry.encrypted:
                        data = PakCrypto.decrypt_block(bytes(data), file_path, encryption_method)
                    file.write(data)
                    return

                for x in PakCrypto.generate_block_indices(len(entry.compressed_blocks), encryption_method):
                    block_data = self._peek_block_content(entry.compressed_blocks[x], encryption_method)
                    if entry.encrypted:
                        block_data = PakCrypto.decrypt_block(bytes(block_data), file_path, encryption_method)

                    decompressed_data = PakCompression.decompress_block(block_data, self._zstd_dict, compression_method)
                    file.write(decompressed_data)

        except OSError as e:
            # Olası "Dosya adı çok uzun" gibi işletim sistemi hatalarını yakalamak için.
            print(f"HATA: Dosya yolu oluşturulurken veya yazılırken bir işletim sistemi hatası oluştu: {file_path}")
            print(f"Detay: {e}")
        except Exception as e:
            # Diğer beklenmedik hataları yakalamak için.
            print(f"HATA: _write_to_disk sırasında beklenmedik bir hata: {file_path}")
            print(f"Detay: {e}")

    def dump(self, out_path: Path) -> None:
        out_path /= self._mount_point

        for dir_path, dir_content in self._index.items():
            current_out_path = out_path / dir_path
            current_out_path.mkdir(parents=True, exist_ok=True)
            for file_name, entry in dir_content.items():
                self._write_to_disk(current_out_path / file_name, entry)