from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from datetime import datetime
from models import db
from models.supply import SupplyRequisition
from decorators import login_required

scanner_bp = Blueprint('scanner', __name__)


@scanner_bp.route('/scanner')
@login_required
def scan():
    return render_template('scanner/scan.html')


@scanner_bp.route('/api/get_item/<uuid:barcode_uuid>')
@login_required
def get_item(barcode_uuid):
    item = SupplyRequisition.query.filter_by(barcode_uuid=barcode_uuid).first()
    if not item:
        return jsonify({'error': 'ไม่พบรายการนี้ในระบบ'}), 404

    return jsonify({
        'sequence_no': item.sequence_no,
        'barcode_uuid': str(item.barcode_uuid),
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
        'requisition_number': item.requisition_number,
        'transaction_date': item.transaction_date.isoformat() if item.transaction_date else None,
        'responsible_person': item.responsible_person,
        'responsible_phone': item.responsible_phone,
        'last_verified_by': item.verifier.username if item.verifier else None,
        'last_verified_at': item.last_verified_at.isoformat() if item.last_verified_at else None,
    })


@scanner_bp.route('/api/verify/<uuid:barcode_uuid>', methods=['POST'])
@login_required
def verify_item(barcode_uuid):
    item = SupplyRequisition.query.filter_by(barcode_uuid=barcode_uuid).first()
    if not item:
        return jsonify({'error': 'ไม่พบรายการนี้ในระบบ'}), 404

    item.verified = True
    item.last_verified_by = current_user.id
    item.last_verified_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'message': 'ยืนยันข้อมูลสำเร็จ'})


@scanner_bp.route('/api/update/<uuid:barcode_uuid>', methods=['POST'])
@login_required
def update_item(barcode_uuid):
    item = SupplyRequisition.query.filter_by(barcode_uuid=barcode_uuid).first()
    if not item:
        return jsonify({'error': 'ไม่พบรายการนี้ในระบบ'}), 404

    data = request.get_json() or {}

    fields = [
        'item_number', 'original_item', 'requisition_item', 'item_name',
        'issuing_unit', 'requisition_unit', 'issued_to', 'supply_control_section',
        'supply_borrowing_unit', 'status', 'unit_of_measure', 'remarks',
        'supply_type', 'requisition_number', 'responsible_person', 'responsible_phone',
    ]
    for field in fields:
        if field in data:
            setattr(item, field, data[field])

    if 'quantity' in data:
        item.quantity = data['quantity']
    if 'has_requisition' in data:
        item.has_requisition = data['has_requisition']
    if 'transaction_date' in data and data['transaction_date']:
        from datetime import date
        item.transaction_date = date.fromisoformat(data['transaction_date'])

    item.verified = True
    item.last_verified_by = current_user.id
    item.last_verified_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'message': 'บันทึกข้อมูลสำเร็จ'})
