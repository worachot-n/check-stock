import barcode
from barcode.writer import ImageWriter
import io


def make_barcode_png(uuid_str: str) -> bytes:
    writer = ImageWriter()
    code = barcode.get('code128', uuid_str, writer=writer)
    buf = io.BytesIO()
    code.write(buf, options={
        'module_width': 0.8,
        'module_height': 8.0,
        'quiet_zone': 2.0,
        'font_size': 6,
        'text_distance': 2.0,
    })
    buf.seek(0)
    return buf.read()
