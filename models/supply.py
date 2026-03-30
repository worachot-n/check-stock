import uuid
from models import db


class SupplyRequisition(db.Model):
    __tablename__ = 'supply_requisitions'

    sequence_no = db.Column(db.Integer, primary_key=True)
    barcode_uuid = db.Column(
        db.UUID(as_uuid=True),
        nullable=False,
        unique=True,
        default=uuid.uuid4
    )
    item_number = db.Column(db.String(50))
    original_item = db.Column(db.String(255))
    requisition_item = db.Column(db.String(255))
    item_name = db.Column(db.String(255))
    issuing_unit = db.Column(db.String(100))
    requisition_unit = db.Column(db.String(100))
    issued_to = db.Column(db.String(100))
    supply_control_section = db.Column(db.String(100))
    supply_borrowing_unit = db.Column(db.String(100))
    status = db.Column(db.String(50))
    verified = db.Column(db.Boolean, default=False)
    quantity = db.Column(db.Numeric(10, 2))
    unit_of_measure = db.Column(db.String(50))
    remarks = db.Column(db.Text)
    supply_type = db.Column(db.String(100))
    has_requisition = db.Column(db.Boolean)
    requisition_number = db.Column(db.String(100))
    transaction_date = db.Column(db.Date)
    responsible_person = db.Column(db.String(100))
    responsible_phone = db.Column(db.String(20))
    last_verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    last_verified_at = db.Column(db.DateTime)

    verifier = db.relationship('User', foreign_keys=[last_verified_by])

    def __repr__(self):
        return f'<SupplyRequisition {self.sequence_no} {self.item_name}>'
