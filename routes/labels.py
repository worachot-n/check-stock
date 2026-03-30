import io
from flask import Blueprint, render_template, request, send_file, jsonify
from models import db
from models.supply import SupplyRequisition
from decorators import login_required
from utils.barcode_gen import make_barcode_png
from fpdf import FPDF
import tempfile, os

labels_bp = Blueprint('labels', __name__)


@labels_bp.route('/inventory')
@login_required
def inventory():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    query = SupplyRequisition.query
    if search:
        query = query.filter(
            SupplyRequisition.item_name.ilike(f'%{search}%') |
            SupplyRequisition.item_number.ilike(f'%{search}%') |
            SupplyRequisition.requisition_item.ilike(f'%{search}%')
        )
    items = query.order_by(SupplyRequisition.sequence_no).paginate(page=page, per_page=50)
    return render_template('inventory/list.html', items=items, search=search)


@labels_bp.route('/labels/generate', methods=['POST'])
@login_required
def generate_labels():
    data = request.get_json() or {}
    uuids = data.get('uuids', [])

    if not uuids:
        return jsonify({'error': 'กรุณาเลือกรายการอย่างน้อย 1 รายการ'}), 400

    items = SupplyRequisition.query.filter(
        SupplyRequisition.barcode_uuid.in_(uuids)
    ).all()

    pdf_bytes = build_label_pdf(items)
    buf = io.BytesIO(pdf_bytes)
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=False,
        download_name='labels.pdf'
    )


def build_label_pdf(items):
    font_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'fonts', 'THSarabunNew.ttf')
    font_path = os.path.abspath(font_path)

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=False)

    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path)
        use_thai_font = True
    else:
        use_thai_font = False

    # A4: 210 x 297 mm
    margin_left = 8
    margin_top = 10
    label_w = 62
    label_h = 40
    cols = 3
    col_gap = (210 - margin_left * 2 - label_w * cols) / (cols - 1)

    col = 0
    row = 0
    max_rows = int((297 - margin_top * 2) // label_h)

    for item in items:
        if col == 0 and row == 0:
            pdf.add_page()

        x = margin_left + col * (label_w + col_gap)
        y = margin_top + row * label_h

        # Border
        pdf.set_draw_color(180, 180, 180)
        pdf.rect(x, y, label_w, label_h)

        # Barcode image
        barcode_bytes = make_barcode_png(str(item.barcode_uuid))
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(barcode_bytes)
            tmp_path = tmp.name

        try:
            pdf.image(tmp_path, x=x + 1, y=y + 1, w=label_w - 2, h=16)
        finally:
            os.unlink(tmp_path)

        # Text
        if use_thai_font:
            pdf.set_font('THSarabun', size=7)
        else:
            pdf.set_font('Helvetica', size=6)

        text_y = y + 18
        line_h = 4.5

        uuid_short = str(item.barcode_uuid)[:18] + '...'
        pdf.set_xy(x + 1, text_y)
        pdf.cell(label_w - 2, line_h, uuid_short, ln=1)

        pdf.set_xy(x + 1, text_y + line_h)
        item_no = f"เลขที่: {item.item_number or '-'}"
        pdf.cell(label_w - 2, line_h, item_no, ln=1)

        pdf.set_xy(x + 1, text_y + line_h * 2)
        req_item = (item.requisition_item or item.item_name or '')[:28]
        pdf.cell(label_w - 2, line_h, req_item, ln=1)

        pdf.set_xy(x + 1, text_y + line_h * 3)
        unit = f"หน่วย: {(item.issuing_unit or '-')[:20]}"
        pdf.cell(label_w - 2, line_h, unit, ln=1)

        col += 1
        if col >= cols:
            col = 0
            row += 1
            if row >= max_rows:
                row = 0

    return bytes(pdf.output())
