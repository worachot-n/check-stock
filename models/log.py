from flask_login import current_user
from models import db


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    sequence_no = db.Column(
        db.Integer,
        db.ForeignKey('supply_requisitions.sequence_no', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    action = db.Column(db.String(50), nullable=False)   # create | edit | verify | delete
    action_detail = db.Column(db.Text)
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    performed_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    performer = db.relationship('User', foreign_keys=[performed_by])

    ACTION_LABELS = {
        'create': 'สร้างรายการ',
        'edit':   'แก้ไขข้อมูล',
        'verify': 'ยืนยันข้อมูล',
        'delete': 'ลบรายการ',
    }

    @property
    def action_label(self):
        return self.ACTION_LABELS.get(self.action, self.action)


def write_log(seq_no: int, action: str, detail: str = None):
    """Add a log entry. Must be called within an active session; caller commits."""
    log = ActivityLog(
        sequence_no=seq_no,
        action=action,
        action_detail=detail,
        performed_by=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(log)
