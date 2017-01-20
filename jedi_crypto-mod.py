'''
fw file: 
With fw of controller, it is possible to do interesting things like:
 * flash custom fw to controller
 * learn how all aspects of controller works
 * implement native pairing on other host devices
 * present custom hardware as "official" DS4 to PS4
The following code shows how to do the first stage of auth - authenticating
over USB in order to have console send the bluetooth link key and host address.
(C) HAXX
'''

import struct
import binascii
from Crypto.Cipher import AES
from Crypto.Hash import SHA256, CMAC
from Crypto.PublicKey import RSA
from Crypto.Signature import pss
from Crypto.Util.number import bytes_to_long
from Crypto.Random import get_random_bytes
from Crypto.Math.Numbers import Integer

hw_bindings = [
    (0x40015fe0, 0x00000004),
    (0x40015fe4, 0x00000018),
    (0x40015fe8, 0x00000014),
    (0x40015fec, 0x00000000),
    (0x40015ff0, 0x0000000d),
    (0x40015ff4, 0x000000f0),
    (0x40015ff8, 0x00000005),
    (0x40015ffc, 0x000000b1),
    (0x4002f000, 0xf3b002c0),
    (0xe00fffe0, 0x00000034),
    (0xe00fffe4, 0x0000004a),
    (0xe00fffe8, 0x00000008),
    (0xe00fffec, 0x00000000),
    (0xe00ffff0, 0x0000000d),
    (0xe00ffff4, 0x00000010),
    (0xe00ffff8, 0x00000005),
    (0xe00ffffc, 0x000000b1),
]

bldr_key_blob = bytes([0x39, 0xFF, 0x1A, 0x67, 0x2B, 0x4F, 0x99, 0xA6, 0xA1, 0xCA,
                       0x65, 0xC2, 0x99, 0xD6, 0x27, 0x0C, 0x7D, 0x4E, 0x1A, 0xF9,
                       0x10, 0x36, 0xAD, 0x6C, 0x8D, 0x20, 0xEA, 0xD1, 0xFF, 0x33,
                       0xD9, 0x03, 0x94, 0xFD, 0x44, 0x15, 0xB5, 0x40, 0x72, 0xD9,
                       0xC8, 0x3B, 0x94, 0x99, 0x43, 0x04, 0xFD, 0x49])
app_key0_blob = bytes([0x3E, 0x5C, 0x05, 0xC6, 0xAF, 0xAF, 0xAB, 0x02, 0x20, 0x3B,
                       0x3D, 0x18, 0x17, 0x33, 0xDD, 0xCB, 0xA9, 0x65, 0x40, 0x0F,
                       0xD5, 0x3A, 0x6F, 0x50, 0x17, 0x31, 0xF3, 0x86, 0x55, 0xB2,
                       0x08, 0x08, 0xCF, 0xB8, 0xE6, 0x18, 0x1C, 0xC9, 0x1D, 0x64,
                       0xC4, 0x99, 0x3B, 0x04, 0x0B, 0xEC, 0xC7, 0xB5, 0xED, 0x18,
                       0xA5, 0x68, 0x3A, 0x95, 0xA3, 0x38, 0xF3, 0xCA, 0x32, 0x55,
                       0x28, 0xA9, 0x6F, 0xCB])
app_key1_blob = bytes([0x7F, 0x81, 0x48, 0x8F, 0x32, 0x02, 0x4C, 0x6B, 0xF5, 0xD9,
                       0x99, 0x92, 0x87, 0x98, 0xAE, 0xC0, 0x78, 0x5F, 0xC3, 0xE6,
                       0x1B, 0xAF, 0x32, 0xDF, 0xA5, 0x83, 0x3F, 0x43, 0x49, 0x64,
                       0xCD, 0x53, 0x37, 0x52, 0x52, 0x39, 0xB1, 0x0B, 0xF8, 0x38,
                       0xEF, 0x29, 0xB3, 0x7E, 0xBD, 0x73, 0xD9, 0x51, 0x1E, 0xC4,
                       0xDF, 0xFB, 0x97, 0x25, 0xA1, 0xE9, 0xD2, 0x67, 0x89, 0x90,
                       0xA0, 0x3C, 0x28, 0x32])

# pubkey of the CA which signs controller keys
jedi_CA_pubkey = RSA.construct((bytes_to_long(bytes([
    0x8E, 0xD7, 0xF9, 0xE4, 0xAA, 0x5C, 0xC5, 0xD2, 0x31, 0x96,
    0xF0, 0xDE, 0x79, 0x7D, 0xFE, 0xAC, 0xF6, 0x3E, 0xDE, 0x7B,
    0xC9, 0x67, 0x16, 0xF1, 0x3C, 0xF5, 0x2A, 0xDE, 0xF8, 0xDA,
    0xCF, 0xA8, 0xE2, 0x33, 0xDC, 0x65, 0x57, 0x17, 0x34, 0x7D,
    0x4C, 0x8C, 0x82, 0x6E, 0xAB, 0x90, 0x36, 0x16, 0xFF, 0x9F,
    0xB8, 0xF9, 0x73, 0x36, 0x17, 0xFB, 0xD4, 0x4E, 0xC8, 0x10,
    0x78, 0xAD, 0x6E, 0x24, 0xB0, 0x62, 0x61, 0x9F, 0x5A, 0x17,
    0xEE, 0x2F, 0x55, 0x72, 0xB4, 0x27, 0xC0, 0x34, 0xA9, 0x49,
    0x36, 0x3E, 0x86, 0xD3, 0xB2, 0x13, 0x35, 0x1F, 0x89, 0x04,
    0xA4, 0x99, 0xF8, 0x62, 0x40, 0x1F, 0x4E, 0x60, 0xAC, 0x21,
    0x31, 0xCD, 0x4B, 0xB9, 0xFD, 0xDF, 0xD5, 0x90, 0xC8, 0xE2,
    0x2B, 0x7D, 0xF9, 0x6D, 0x01, 0x5A, 0x41, 0xC5, 0x49, 0xF3,
    0xEA, 0x0D, 0xED, 0xFC, 0x32, 0xCE, 0xC3, 0x2D, 0x72, 0xC5,
    0x34, 0x93, 0x4A, 0xEF, 0x3D, 0xD1, 0x2B, 0x58, 0xDB, 0x35,
    0x7D, 0xD0, 0x4D, 0x9A, 0x93, 0x11, 0xA3, 0x83, 0x3F, 0xF8,
    0x55, 0x7A, 0x0B, 0x85, 0xB4, 0x54, 0xCD, 0x21, 0xDA, 0xB9,
    0x0D, 0x71, 0x4A, 0xEA, 0x2D, 0xEC, 0x42, 0xE6, 0xF4, 0xEF,
    0x20, 0x45, 0x3C, 0xF6, 0xDB, 0xF3, 0x95, 0x4E, 0x73, 0xA8,
    0x76, 0x91, 0xCF, 0xA0, 0x3F, 0x47, 0x59, 0x45, 0x5C, 0x8B,
    0x96, 0xF1, 0xD0, 0xB6, 0x9D, 0xD3, 0xDD, 0x62, 0x62, 0xE9,
    0x43, 0x8D, 0xCC, 0x26, 0x96, 0xCF, 0xE6, 0x4B, 0x93, 0x0C,
    0x6E, 0x7D, 0x4E, 0x01, 0x51, 0xF6, 0xD1, 0xB1, 0x5D, 0x1A,
    0x4B, 0xE2, 0xE6, 0x0F, 0x0B, 0x36, 0x11, 0x8C, 0x60, 0xF2,
    0x53, 0xFD, 0xBC, 0xE2, 0x27, 0xA8, 0xA4, 0xC9, 0xCD, 0xF2,
    0x26, 0x08, 0x58, 0x58, 0x4A, 0xB8, 0xD7, 0x1C, 0x62, 0x9C,
    0xD4, 0x21, 0xEC, 0x66, 0x60, 0x59])), 0x10001))


def get_hw_binding():
    binding = []
    for addr, val in hw_bindings:
        binding.append(struct.pack('<L', val))
    return b''.join(binding)


def unwrap_key_blob(blob):
    return HwKey().decrypt_and_verify(blob)


class JediKey:

    def decrypt(s, buf): return AES.new(s.key, AES.MODE_CBC, s.iv).decrypt(buf)

    def verify(s, buf):
        content, mac = buf[:-0x10], buf[-0x10:]
        CMAC.new(s.cmac_key, ciphermod=AES, msg=content).verify(mac)
        return content

    def decrypt_and_verify(s, buf): return s.verify(s.decrypt(buf))


class HwKey(JediKey):

    def __init__(s):
        s.key = SHA256.new(get_hw_binding()).digest()[:0x10]
        s.cmac_key = s.key
        s.iv = b'\0' * 16


class BldrKey(JediKey):

    def __init__(s):
        blob = unwrap_key_blob(bldr_key_blob)
        # decrypts fw image with {key=blob[0:0x10], iv= 0}
        # verifies fw image with {cmac_key = blob[0x10:0x20]}
        s.key, s.cmac_key, s.iv = blob[:0x10], blob[0x10:0x20], b'\0' * 16


class AppKey(JediKey):

    def __init__(s, key_id):
        assert key_id in (0, 1)
        blob = unwrap_key_blob(app_key0_blob if key_id == 0 else app_key1_blob)
        s.key, s.iv, s.cmac_key = blob[:0x10], blob[0x10:0x20], blob[0x20:0x30]


class JediCert:

    def __init__(s, cert_file):
        s.serial = str(cert_file[0x5a0:0x5a0 + 0x10], 'ascii')
        s.key = s.construct_key(s.decrypt(cert_file[:0x5a0]))

    def decrypt(s, buf):
        for i in range(2):
            try:
                return AppKey(i).decrypt_and_verify(buf)
            except ValueError:
                pass
        raise Exception('failed to decrypt cert')

    def construct_key(s, buf):
        ''' binary format is:
        u8 serial_bin[0x10]
        u8 n[0x100]
        u8 e[0x100]
        u8 sig[0x100]
        u8 p[0x80]
        u8 q[0x80]
        u8 dp[0x80]
        u8 dq[0x80]
        u8 qinv[0x80]
        '''
        pos = 0
        serial_bin = buf[pos:pos + 0x10]
        pos += 0x10
        n = buf[pos:pos + 0x100]
        pos += 0x100
        e = buf[pos:pos + 0x100]
        pos += 0x100
        sig = buf[pos:pos + 0x100]
        pos += 0x100
        p = buf[pos:pos + 0x80]
        pos += 0x80
        q = buf[pos:pos + 0x80]

        # extraneous sanity check
        assert binascii.unhexlify(s.serial) == serial_bin[-8:]
        # our serial number and pubkey should be validly signed by the CA
        pss.new(jedi_CA_pubkey).verify(SHA256.new(serial_bin + n + e), sig)

        n = bytes_to_long(n)
        e = bytes_to_long(e)
        p = bytes_to_long(p)
        q = bytes_to_long(q)
        key = RSA.construct((
            n, e,
            Integer(e).inverse((p - 1) * (q - 1)), p, q
        ))
        #open('./jedi_cert.bin', 'wb').write(buf)
        return key

    def sign(s, msg):
        return pss.new(s.key).sign(SHA256.new(msg))


class JediFlash:

    def __init__(s, path):
        s.path = path
        s.verify_fw()
        s.cert = JediCert(s.read_interleaved(0x5000, 0x800))

    def verify_fw(s):
        with open(s.path, 'rb') as f:
            f.seek(0x8000)
            BldrKey().verify(f.read(0x38000))

    def read_interleaved(s, addr, size):
        assert (addr % 4) == 0
        assert (size % 4) == 0
        with open(s.path, 'rb') as f:
            f.seek(addr)
            buf = []
            while size > 0:
                buf.append(f.read(4))
                f.seek(4, 1)
                size -= 4
        return b''.join(buf)


if __name__ == '__main__':
    flash = JediFlash('./jedi_flash-Aug_3_2013.bin')
    cert = flash.cert

    # example of what usb auth does

    # console gens and sends the nonce..
    nonce = get_random_bytes(0x100)
    # controller signs it and sends back pubkey and sig
    jedi_sig = cert.sign(nonce)
    # console checks sig...
    pss.new(cert.key.publickey()).verify(SHA256.new(nonce), jedi_sig)

    print(r'\o/')

    # now, console will send controller bt link key + host addr
    # then controller must respond to bt challenges, but they are much more
    # simple

	#GodzIvan 
    open('./jedi_PrivateKey.pem', 'wb').write(cert.key.exportKey())
    open('./jedi_PrivateKey.der', 'wb').write(cert.key.exportKey("DER"))
    open('./jedi_PublicKey.pem', 'wb').write(cert.key.publickey().exportKey())
    open('./jedi_PublicKey.der', 'wb').write(cert.key.publickey().exportKey("DER"))
	
    print(r'Test nonce')
	
    # console gens and sends the nonce..
    ps4nonce = open('./ps4nonce.bin', 'rb').read()
    # controller signs it and sends back pubkey and sig
    ds4_sig = open('./ds4sig.bin', 'rb').read()
    # console checks sig...
    pss.new(cert.key.publickey()).verify(SHA256.new(ps4nonce), ds4_sig)

	