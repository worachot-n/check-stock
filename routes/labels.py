import io
from flask import Blueprint, render_template, request, send_file, jsonify
from sqlalchemy import text
from models import db
from models.supply import SupplyRequisition
from decorators import login_required
from utils.barcode_gen import make_barcode_png
from fpdf import FPDF
import tempfile, os

labels_bp = Blueprint('labels', __name__)

PER_PAGE = 50


@labels_bp.route('/inventory')
@login_required
def inventory():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    search_like = f'%{search}%' if search else '%'
    params = {'search_like': search_like}

    where = """
        WHERE (:search_like = '%'
               OR COALESCE(requisition_item, item_name) ILIKE :search_like
               OR item_number ILIKE :search_like)
    """

    total_rows = db.session.execute(text(f"""
        SELECT COUNT(*) FROM (
            SELECT COALESCE(requisition_item, item_name)
            FROM supply_requisitions
            {where}
            GROUP BY COALESCE(requisition_item, item_name)
        ) sub
    """), params).scalar()

    rows = db.session.execute(text(f"""
        SELECT
            COALESCE(requisition_item, item_name)          AS display_name,
            STRING_AGG(DISTINCT item_number, ', ')         AS item_numbers,
            SUM(quantity)                                  AS total_quantity,
            MAX(unit_of_measure)                           AS unit_of_measure,
            MAX(issuing_unit)                              AS issuing_unit,
            STRING_AGG(CAST(sequence_no AS TEXT), ',')     AS seq_nos,
            BOOL_AND(verified)                             AS all_verified,
            COUNT(*)                                       AS item_count
        FROM supply_requisitions
        {where}
        GROUP BY COALESCE(requisition_item, item_name)
        ORDER BY display_name
        LIMIT :limit OFFSET :offset
    """), {**params, 'limit': PER_PAGE, 'offset': (page - 1) * PER_PAGE}).fetchall()

    total_pages = max(1, (total_rows + PER_PAGE - 1) // PER_PAGE)

    pagination = {
        'page': page,
        'pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1,
        'next_num': page + 1,
        'total': total_rows,
    }

    return render_template('inventory/list.html', rows=rows, pagination=pagination, search=search)


@labels_bp.route('/labels/generate', methods=['POST'])
@login_required
def generate_labels():
    data = request.get_json() or {}
    seq_nos = [int(s) for s in data.get('seq_nos', []) if str(s).isdigit()]

    if not seq_nos:
        return jsonify({'error': 'กรุณาเลือกรายการอย่างน้อย 1 รายการ'}), 400

    items = SupplyRequisition.query.filter(
        SupplyRequisition.sequence_no.in_(seq_nos)
    ).order_by(SupplyRequisition.sequence_no).all()

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

        pdf.set_draw_color(180, 180, 180)
        pdf.rect(x, y, label_w, label_h)

        # Barcode from sequence_no
        barcode_bytes = make_barcode_png(str(item.sequence_no))
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(barcode_bytes)
            tmp_path = tmp.name

        try:
            pdf.image(tmp_path, x=x + 1, y=y + 1, w=label_w - 2, h=16)
        finally:
            os.unlink(tmp_path)

        if use_thai_font:
            pdf.set_font('THSarabun', size=7)
        else:
            pdf.set_font('Helvetica', size=6)

        text_y = y + 18
        line_h = 4.5

        pdf.set_xy(x + 1, text_y)
        pdf.cell(label_w - 2, line_h, f"ลำดับที่: {item.sequence_no}", ln=1)

        pdf.set_xy(x + 1, text_y + line_h)
        pdf.cell(label_w - 2, line_h, f"เลขที่: {item.item_number or '-'}", ln=1)

        pdf.set_xy(x + 1, text_y + line_h * 2)
        req_item = (item.requisition_item or item.item_name or '')[:28]
        pdf.cell(label_w - 2, line_h, req_item, ln=1)

        pdf.set_xy(x + 1, text_y + line_h * 3)
        pdf.cell(label_w - 2, line_h, f"หน่วย: {(item.issuing_unit or '-')[:20]}", ln=1)

        col += 1
        if col >= cols:
            col = 0
            row += 1
            if row >= max_rows:
                row = 0

    return bytes(pdf.output())
