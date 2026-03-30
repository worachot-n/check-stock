from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from datetime import datetime, date as date_type
from models import db
from models.supply import SupplyRequisition
from decorators import login_required
from utils.uploads import save_file, delete_file, file_url
from models.log import write_log

scanner_bp = Blueprint('scanner', __name__)


@scanner_bp.route('/scanner')
@login_required
def scan():
    return render_template('scanner/scan.html')


@scanner_bp.route('/api/get_item/<int:sequence_no>')
@login_required
def get_item(sequence_no):
    item = SupplyRequisition.query.get(sequence_no)
    if not item:
        return jsonify({'error': 'ไม่พบรายการนี้ในระบบ'}), 404

    return jsonify({
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
        'last_verified_by': item.verifier.username if item.verifier else None,
        'last_verified_at': item.last_verified_at.isoformat() if item.last_verified_at else None,
    })


@scanner_bp.route('/api/verify/<int:sequence_no>', methods=['POST'])
@login_required
def verify_item(sequence_no):
    item = SupplyRequisition.query.get(sequence_no)
    if not item:
        return jsonify({'error': 'ไม่พบรายการนี้ในระบบ'}), 404

    item.verified = True
    item.last_verified_by = current_user.id
    item.last_verified_at = datetime.utcnow()
    write_log(sequence_no, 'verify')
    db.session.commit()
    return jsonify({'success': True, 'message': 'ยืนยันข้อมูลสำเร็จ'})


@scanner_bp.route('/api/update/<int:sequence_no>', methods=['POST'])
@login_required
def update_item(sequence_no):
    item = SupplyRequisition.query.get(sequence_no)
    if not item:
        return jsonify({'error': 'ไม่พบรายการนี้ในระบบ'}), 404

    # Accept multipart/form-data (supports file uploads)
    data = request.form

    str_fields = [
        'item_number', 'original_item', 'requisition_item', 'item_name',
        'issuing_unit', 'requisition_unit', 'issued_to', 'supply_control_section',
        'supply_borrowing_unit', 'status', 'unit_of_measure', 'remarks',
        'supply_type', 'responsible_person', 'responsible_phone',
    ]
    for field in str_fields:
        if field in data:
            setattr(item, field, data[field] or None)

    if 'quantity' in data:
        item.quantity = data['quantity'] or None
    if 'has_requisition' in data:
        item.has_requisition = data['has_requisition'] == 'true'
    if 'transaction_date' in data:
        val = data['transaction_date']
        item.transaction_date = date_type.fromisoformat(val) if val else None

    # File uploads
    files = request.files
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

    item.verified = True
    item.last_verified_by = current_user.id
    item.last_verified_at = datetime.utcnow()
    write_log(sequence_no, 'edit')
    db.session.commit()
    return jsonify({'success': True, 'message': 'บันทึกข้อมูลสำเร็จ'})
