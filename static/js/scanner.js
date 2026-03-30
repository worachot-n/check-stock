let currentSeqNo = null;
let html5QrcodeScanner = null;

function onScanSuccess(decodedText) {
    const seq = parseInt(decodedText.trim(), 10);
    if (isNaN(seq)) {
        showError('บาร์โค้ดไม่ใช่ตัวเลข ลำดับที่ไม่ถูกต้อง');
        return;
    }
    fetchItem(seq);
}

function onScanFailure(error) {
    // silent
}

function initScanner() {
    html5QrcodeScanner = new Html5QrcodeScanner(
        "reader",
        {
            fps: 10,
            qrbox: { width: 280, height: 120 },
            formatsToSupport: [
                Html5QrcodeSupportedFormats.CODE_128,
                Html5QrcodeSupportedFormats.QR_CODE,
                Html5QrcodeSupportedFormats.EAN_13,
            ],
        },
        false
    );
    html5QrcodeScanner.render(onScanSuccess, onScanFailure);
}

function fetchItem(seqNo) {
    hideError();
    fetch(`/api/get_item/${seqNo}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
                return;
            }
            currentSeqNo = data.sequence_no;
            populateForm(data);
        })
        .catch(() => showError('เกิดข้อผิดพลาดในการเชื่อมต่อ'));
}

function lookupManual() {
    const val = document.getElementById('manual-seq').value.trim();
    const seq = parseInt(val, 10);
    if (!val || isNaN(seq)) {
        showError('กรุณาพิมพ์เลขลำดับที่ (sequence_no)');
        return;
    }
    fetchItem(seq);
}

function populateForm(data) {
    const fields = [
        'item_number', 'item_name', 'requisition_item', 'original_item',
        'quantity', 'unit_of_measure', 'issuing_unit', 'requisition_unit',
        'issued_to', 'status', 'responsible_person', 'responsible_phone',
        'transaction_date', 'requisition_number', 'remarks'
    ];

    fields.forEach(f => {
        const el = document.getElementById('f-' + f);
        if (el) el.value = data[f] ?? '';
    });

    document.getElementById('f-seq-no').textContent = data.sequence_no;

    const badge = document.getElementById('verified-badge');
    badge.classList.toggle('hidden', !data.verified);

    const info = document.getElementById('last-verified-info');
    if (data.last_verified_by) {
        info.textContent = `ตรวจสอบล่าสุดโดย: ${data.last_verified_by} เมื่อ ${data.last_verified_at || ''}`;
    } else {
        info.textContent = 'ยังไม่เคยตรวจสอบ';
    }

    document.getElementById('item-card').classList.remove('hidden');
}

function verifyItem() {
    if (!currentSeqNo) return;
    fetch(`/api/verify/${currentSeqNo}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('verified-badge').classList.remove('hidden');
                showSuccess('ยืนยันข้อมูลสำเร็จ');
            } else {
                showError(data.error || 'เกิดข้อผิดพลาด');
            }
        })
        .catch(() => showError('เกิดข้อผิดพลาดในการเชื่อมต่อ'));
}

function updateItem() {
    if (!currentSeqNo) return;
    const payload = {
        item_number: document.getElementById('f-item_number').value,
        item_name: document.getElementById('f-item_name').value,
        requisition_item: document.getElementById('f-requisition_item').value,
        original_item: document.getElementById('f-original_item').value,
        quantity: parseFloat(document.getElementById('f-quantity').value) || null,
        unit_of_measure: document.getElementById('f-unit_of_measure').value,
        issuing_unit: document.getElementById('f-issuing_unit').value,
        requisition_unit: document.getElementById('f-requisition_unit').value,
        issued_to: document.getElementById('f-issued_to').value,
        status: document.getElementById('f-status').value,
        responsible_person: document.getElementById('f-responsible_person').value,
        responsible_phone: document.getElementById('f-responsible_phone').value,
        transaction_date: document.getElementById('f-transaction_date').value || null,
        requisition_number: document.getElementById('f-requisition_number').value,
        remarks: document.getElementById('f-remarks').value,
    };

    fetch(`/api/update/${currentSeqNo}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            document.getElementById('verified-badge').classList.remove('hidden');
            showSuccess('บันทึกข้อมูลสำเร็จ');
        } else {
            showError(data.error || 'เกิดข้อผิดพลาด');
        }
    })
    .catch(() => showError('เกิดข้อผิดพลาดในการเชื่อมต่อ'));
}

function showError(msg) {
    const el = document.getElementById('error-msg');
    el.textContent = msg;
    el.className = 'bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg text-sm';
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 5000);
}

function showSuccess(msg) {
    const el = document.getElementById('error-msg');
    el.textContent = msg;
    el.className = 'bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg text-sm';
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 3000);
}

function hideError() {
    document.getElementById('error-msg').classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', initScanner);

document.getElementById('manual-seq').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') lookupManual();
});
