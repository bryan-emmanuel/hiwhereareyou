import io
import qrcode
from src.core.interfaces import QRProvider

class QRCodeGenerator(QRProvider):
    def generate_qr_code(self, data: str) -> bytes:
        """
        Generates a standard black and white QR code image as PNG bytes.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        return img_bytes.getvalue()
