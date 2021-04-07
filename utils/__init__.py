import base64
import hashlib

from Crypto.Cipher import AES


class AESEncoder:

    def __init__(self, key, iv):
        self.key = hashlib.sha256(key.encode()).digest()
        self.iv = iv  # pylint: disable=invalid-name

    def encrypt(self, raw):
        raw = self.pad(raw)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return base64.b64encode(cipher.encrypt(raw.encode())).decode('utf-8')

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return self.rm_pad(cipher.decrypt(enc)).decode('utf-8')

    @staticmethod
    def pad(text):
        block_size = AES.block_size
        placeholder_len = block_size - len(text) % block_size
        return text + placeholder_len * chr(placeholder_len)

    @staticmethod
    def rm_pad(text):
        return text[:-ord(text[len(text)-1:])]
