"""TOTP (Time-based One-Time Password) service for two-factor authentication.

Uses pyotp for TOTP generation/verification and QR code generation for setup.
"""

from __future__ import annotations

import base64
import io
import secrets
from typing import TYPE_CHECKING

from flowforge_server.services.crypto import decrypt_value, encrypt_value

if TYPE_CHECKING:
    pass


# Number of backup codes to generate
BACKUP_CODE_COUNT = 10

# Length of each backup code (characters)
BACKUP_CODE_LENGTH = 8

# TOTP configuration
TOTP_ISSUER = "FlowForge"
TOTP_DIGITS = 6
TOTP_INTERVAL = 30


def generate_totp_secret() -> str:
    """
    Generate a new TOTP secret.

    Returns:
        Base32-encoded secret suitable for TOTP
    """
    try:
        import pyotp
        return pyotp.random_base32()
    except ImportError:
        raise ImportError(
            "pyotp is required for 2FA. Install with: pip install pyotp"
        )


def get_provisioning_uri(secret: str, email: str) -> str:
    """
    Generate a provisioning URI for authenticator apps.

    Args:
        secret: The TOTP secret (base32)
        email: User's email address for account identification

    Returns:
        otpauth:// URI for QR code generation
    """
    try:
        import pyotp
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name=TOTP_ISSUER,
        )
    except ImportError:
        raise ImportError(
            "pyotp is required for 2FA. Install with: pip install pyotp"
        )


def generate_qr_code(provisioning_uri: str) -> str:
    """
    Generate a QR code image for the provisioning URI.

    Args:
        provisioning_uri: The otpauth:// URI

    Returns:
        Base64-encoded PNG image data (data:image/png;base64,...)
    """
    try:
        import qrcode
    except ImportError:
        raise ImportError(
            "qrcode is required for 2FA QR codes. Install with: pip install qrcode"
        )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    # Try different image backends in order of preference
    buffer = io.BytesIO()

    try:
        # Try Pillow first (most common)
        from PIL import Image
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(buffer, format="PNG")
    except ImportError:
        try:
            # Try pypng backend
            from qrcode.image.pure import PyPNGImage
            img = qr.make_image(image_factory=PyPNGImage)
            img.save(buffer)
        except ImportError:
            # Fallback: generate SVG and convert to data URI
            from qrcode.image.svg import SvgImage
            img = qr.make_image(image_factory=SvgImage)
            svg_buffer = io.BytesIO()
            img.save(svg_buffer)
            svg_buffer.seek(0)
            b64_data = base64.b64encode(svg_buffer.getvalue()).decode()
            return f"data:image/svg+xml;base64,{b64_data}"

    buffer.seek(0)
    b64_data = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{b64_data}"


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verify a TOTP code against the secret.

    Args:
        secret: The TOTP secret (base32)
        code: The 6-digit code to verify

    Returns:
        True if the code is valid, False otherwise
    """
    try:
        import pyotp
    except ImportError:
        raise ImportError(
            "pyotp is required for 2FA. Install with: pip install pyotp"
        )

    if not secret or not code:
        return False

    # Clean up the code (remove spaces, etc.)
    code = code.strip().replace(" ", "").replace("-", "")

    # Verify with a small window to account for clock drift
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_backup_codes() -> list[str]:
    """
    Generate a set of backup codes for 2FA recovery.

    Returns:
        List of backup codes
    """
    codes = []
    for _ in range(BACKUP_CODE_COUNT):
        # Generate a random code with format: XXXX-XXXX
        code = secrets.token_hex(BACKUP_CODE_LENGTH // 2).upper()
        formatted_code = f"{code[:4]}-{code[4:]}"
        codes.append(formatted_code)
    return codes


def hash_backup_code(code: str) -> str:
    """
    Hash a backup code for storage.

    Args:
        code: The backup code in any format

    Returns:
        SHA-256 hash of the normalized code
    """
    import hashlib

    # Normalize: remove dashes, spaces, lowercase
    normalized = code.replace("-", "").replace(" ", "").lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def encrypt_totp_secret(secret: str) -> str:
    """
    Encrypt a TOTP secret for storage.

    Args:
        secret: The TOTP secret (base32)

    Returns:
        Encrypted secret
    """
    return encrypt_value(secret)


def decrypt_totp_secret(encrypted_secret: str) -> str:
    """
    Decrypt a stored TOTP secret.

    Args:
        encrypted_secret: The encrypted TOTP secret

    Returns:
        Decrypted TOTP secret (base32)
    """
    return decrypt_value(encrypted_secret)


def encrypt_backup_codes(codes: list[str]) -> list[str]:
    """
    Hash backup codes for storage.

    Note: Backup codes are hashed (not encrypted) because we only need
    to verify them, not retrieve the original values.

    Args:
        codes: List of plain backup codes

    Returns:
        List of hashed backup codes
    """
    return [hash_backup_code(code) for code in codes]


def verify_backup_code(code: str, stored_codes: list[str]) -> tuple[bool, int | None]:
    """
    Verify a backup code against stored hashes.

    Args:
        code: The backup code to verify
        stored_codes: List of hashed backup codes

    Returns:
        Tuple of (is_valid, code_index)
        If valid, returns the index of the used code (for removal)
    """
    if not code or not stored_codes:
        return False, None

    code_hash = hash_backup_code(code)

    for idx, stored_hash in enumerate(stored_codes):
        if stored_hash == code_hash:
            return True, idx

    return False, None


class TOTPSetupData:
    """Data class for TOTP setup response."""

    def __init__(self, secret: str, qr_code: str, provisioning_uri: str):
        self.secret = secret
        self.qr_code = qr_code
        self.provisioning_uri = provisioning_uri


def setup_totp_for_user(email: str) -> TOTPSetupData:
    """
    Generate TOTP setup data for a user.

    Args:
        email: User's email address

    Returns:
        TOTPSetupData with secret, QR code, and provisioning URI
    """
    secret = generate_totp_secret()
    provisioning_uri = get_provisioning_uri(secret, email)
    qr_code = generate_qr_code(provisioning_uri)

    return TOTPSetupData(
        secret=secret,
        qr_code=qr_code,
        provisioning_uri=provisioning_uri,
    )
