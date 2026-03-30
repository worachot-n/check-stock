import io
from datetime import date as date_type
from flask import Blueprint, render_template, request, send_file, jsonify
from sqlalchemy import text
from models import db
from models.supply import SupplyRequisition
from decorators import login_required
from utils.barcode_gen import make_barcode_png
from utils.uploads import save_file, delete_file, file_url
from models.log import ActivityLog, write_log
from fpdf import FPDF
import tempfile, os

labels_bp = Blueprint('labels', __name__)

PER_PAGE = 50


# ─── Inventory list (grouped) ─────────────────────────────────────────────────

@labels_bp.route('/inventory')
@login_required
def inventory():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    section = request.args.get('section', '').strip()

    search_like = f'%{search}%' if search else '%'
    params = {'search_like': search_like, 'section': section or None}

    NAME_EXPR = "COALESCE(NULLIF(requisition_item, ''), item_name)"

    where = f"""
        WHERE (:search_like = '%'
               OR {NAME_EXPR} ILIKE :search_like
               OR item_number ILIKE :search_like)
          AND (:section IS NULL OR supply_control_section = :section)
    """

    # Distinct section list for the filter dropdown
    sections = db.session.execute(text("""
        SELECT DISTINCT supply_control_section
        FROM supply_requisitions
        WHERE supply_control_section IS NOT NULL AND supply_control_section <> ''
        ORDER BY supply_control_section
    """)).scalars().all()

    total_rows = db.session.execute(text(f"""
        SELECT COUNT(*) FROM (
            SELECT {NAME_EXPR}
            FROM supply_requisitions
            {where}
            GROUP BY {NAME_EXPR}
        ) sub
    """), params).scalar()

    rows = db.session.execute(text(f"""
        SELECT
            {NAME_EXPR}                                        AS display_name,
            STRING_AGG(DISTINCT item_number, ', ')             AS item_numbers,
            SUM(quantity)                                      AS total_quantity,
            MAX(unit_of_measure)                               AS unit_of_measure,
            MAX(issuing_unit)                                  AS issuing_unit,
            STRING_AGG(CAST(sequence_no AS TEXT), ',')         AS seq_nos,
            BOOL_AND(verified)                                 AS all_verified,
            COUNT(*)                                           AS item_count,
            MAX(item_image)                                    AS item_image
        FROM supply_requisitions
        {where}
        GROUP BY {NAME_EXPR}
        ORDER BY display_name
        LIMIT :limit OFFSET :offset
    """), {**params, 'limit': PER_PAGE, 'offset': (page - 1) * PER_PAGE}).fetchall()

    total_pages = max(1, (total_rows + PER_PAGE - 1) // PER_PAGE)
    pagination = {
        'page': page, 'pages': total_pages,
        'has_prev': page > 1, 'has_next': page < total_pages,
        'prev_num': page - 1, 'next_num': page + 1, 'total': total_rows,
    }

    return render_template('inventory/list.html', rows=rows, pagination=pagination,
                           search=search, section=section, sections=sections)


# ─── CRUD: individual items ───────────────────────────────────────────────────

@labels_bp.route('/api/group_items')
@login_required
def group_items():
    display_name = request.args.get('group', '').strip()
    if not display_name:
        return jsonify([])

    items = SupplyRequisition.query.filter(
        text("COALESCE(NULLIF(requisition_item, ''), item_name) = :name")
    ).params(name=display_name).order_by(SupplyRequisition.sequence_no).all()

    return jsonify([_to_dict(i) for i in items])


@labels_bp.route('/api/item/<int:seq_no>')
@login_required
def get_item_detail(seq_no):
    item = SupplyRequisition.query.get_or_404(seq_no)
    return jsonify(_to_dict(item))


@labels_bp.route('/api/field_suggestions')
@login_required
def field_suggestions():
    fields = [
        'original_item', 'requisition_item', 'item_name',
        'issuing_unit', 'requisition_unit', 'issued_to',
        'supply_control_section', 'supply_borrowing_unit',
        'status', 'supply_type', 'responsible_person', 'responsible_phone',
    ]
    result = {}
    for field in fields:
        col = getattr(SupplyRequisition, field)
        rows = (
            db.session.query(col)
            .filter(col.isnot(None), col != '')
            .distinct()
            .order_by(col)
            .all()
        )
        result[field] = [r[0] for r in rows if r[0]]
    return jsonify(result)


@labels_bp.route('/api/item/<int:seq_no>/logs')
@login_required
def item_logs(seq_no):
    logs = (
        ActivityLog.query
        .filter_by(sequence_no=seq_no)
        .order_by(ActivityLog.performed_at.desc())
        .all()
    )
    return jsonify([{
        'action':       log.action_label,
        'action_detail': log.action_detail,
        'performed_by': log.performer.username if log.performer else '-',
        'performed_at': log.performed_at.strftime('%d/%m/%Y %H:%M:%S') if log.performed_at else '-',
    } for log in logs])


@labels_bp.route('/inventory/item/add', methods=['POST'])
@login_required
def add_item():
    item = SupplyRequisition()
    _apply_fields(item, request.form)
    db.session.add(item)
    db.session.flush()          # get sequence_no before saving files

    _save_uploads(item, request.files)
    write_log(item.sequence_no, 'create')
    db.session.commit()
    return jsonify({'success': True, 'sequence_no': item.sequence_no})


@labels_bp.route('/inventory/item/<int:seq_no>/edit', methods=['POST'])
@login_required
def edit_item(seq_no):
    item = SupplyRequisition.query.get_or_404(seq_no)
    _apply_fields(item, request.form)
    _save_uploads(item, request.files)
    write_log(seq_no, 'edit')
    db.session.commit()
    return jsonify({'success': True})


@labels_bp.route('/inventory/item/<int:seq_no>/delete', methods=['POST'])
@login_required
def delete_item(seq_no):
    item = SupplyRequisition.query.get_or_404(seq_no)
    write_log(seq_no, 'delete', f'ลบรายการ: {item.requisition_item or item.item_name}')
    delete_file(item.requisition_file, 'requisitions')
    delete_file(item.item_image, 'items')
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})


# ─── PDF Label generation ─────────────────────────────────────────────────────

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
    return send_file(buf, mimetype='application/pdf', as_attachment=False, download_name='labels.pdf')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _apply_fields(item, data):
    str_fields = [
        'item_number', 'original_item', 'requisition_item', 'item_name',
        'issuing_unit', 'requisition_unit', 'issued_to', 'supply_control_section',
        'supply_borrowing_unit', 'status', 'unit_of_measure', 'remarks',
        'supply_type', 'responsible_person', 'responsible_phone',
    ]
    for f in str_fields:
        if f in data:
            setattr(item, f, data[f] or None)
    if 'quantity' in data:
        item.quantity = data['quantity'] or None
    if 'has_requisition' in data:
        item.has_requisition = data['has_requisition']
    if 'transaction_date' in data:
        val = data['transaction_date']
        item.transaction_date = date_type.fromisoformat(val) if val else None


def _save_uploads(item, files):
    if 'requisition_file' in files and files['requisition_file'].filename:
        old = item.requisition_file
        new_name = save_file(files['requisition_file'], 'requisitions', item.sequence_no)
        if new_name:
            if old and old != new_name:
                delete_file(old, 'requisitions')
            item.requisition_file = new_name

    if 'item_image' in files and files['item_image'].filename:
        old = item.item_image
        new_name = save_file(files['item_image'], 'items', item.sequence_no)
        if new_name:
            if old and old != new_name:
                delete_file(old, 'items')
            item.item_image = new_name


def _to_dict(item):
    return {
        'sequence_no': item.sequence_no,
        'item_number': item.item_number,
        'original_item': item.original_item,
        'requisition_item': item.requisition_item,
        'item_name': item.item_name,
        'issuing_unit': item.issuing_unit,
        'requisition_unit': item.requisition_unit,
        'issued_to': item.issued_to,
        'supply_control_section': item.supply_control_section,
        'supply_borrowing_unit': item.supply_borrowing_unit,
        'status': item.status,
        'verified': item.verified,
        'quantity': float(item.quantity) if item.quantity is not None else None,
        'unit_of_measure': item.unit_of_measure,
        'remarks': item.remarks,
        'supply_type': item.supply_type,
        'has_requisition': item.has_requisition,
        'requisition_file': item.requisition_file,
        'requisition_file_url': file_url(item.requisition_file, 'requisitions'),
        'item_image': item.item_image,
        'item_image_url': file_url(item.item_image, 'items'),
        'transaction_date': item.transaction_date.isoformat() if item.transaction_date else None,
        'responsible_person': item.responsible_person,
        'responsible_phone': item.responsible_phone,
    }


def build_label_pdf(items):
    font_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'static', 'fonts', 'THSarabunNew.ttf')
    )

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=False)

    if os.path.exists(font_path):
        pdf.add_font('THSarabun', '', font_path)
        use_thai_font = True
    else:
        use_thai_font = False

    # Layout: 4 columns × 8 rows = 32 labels per A4 page
    margin_left = 6
    margin_top  = 8
    label_w     = 45      # mm
    label_h     = 25      # mm
    cols        = 4
    col_gap     = (210 - margin_left * 2 - label_w * cols) / (cols - 1)  # 6 mm
    max_rows    = int((297 - margin_top * 2) // label_h)                  # 8 rows

    barcode_h   = 10      # barcode image height (mm)
    text_offset = barcode_h + 2     # gap below barcode
    line_h      = 4.0     # line height (mm)
    font_size   = 12

    col = 0
    row = 0

    for item in items:
        if col == 0 and row == 0:
            pdf.add_page()

        x = margin_left + col * (label_w + col_gap)
        y = margin_top  + row * label_h

        pdf.set_draw_color(200, 200, 200)
        pdf.rect(x, y, label_w, label_h)

        barcode_bytes = make_barcode_png(str(item.sequence_no))
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(barcode_bytes)
            tmp_path = tmp.name
        try:
            pdf.image(tmp_path, x=x + 0.5, y=y + 0.5, w=label_w - 1, h=barcode_h)
        finally:
            os.unlink(tmp_path)

        if use_thai_font:
            pdf.set_font('THSarabun', size=font_size)
        else:
            pdf.set_font('Helvetica', size=font_size)

        text_y = y + text_offset

        pdf.set_xy(x + 0.5, text_y)
        pdf.cell(label_w - 1, line_h, f"#{item.sequence_no}  {item.item_number or ''}", ln=1)
        pdf.set_xy(x + 0.5, text_y + line_h)
        pdf.cell(label_w - 1, line_h, (item.requisition_item or item.item_name or '')[:18], ln=1)
        pdf.set_xy(x + 0.5, text_y + line_h * 2)
        pdf.cell(label_w - 1, line_h, (item.issuing_unit or '')[:18], ln=1)

        col += 1
        if col >= cols:
            col = 0
            row += 1
            if row >= max_rows:
                row = 0

    return bytes(pdf.output())
