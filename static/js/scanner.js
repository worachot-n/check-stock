let currentSeqNo = null;

function onScanSuccess(decodedText) {
    const seq = parseInt(decodedText.trim(), 10);
    if (isNaN(seq)) { showError('บาร์โค้ดไม่ใช่ตัวเลข'); return; }
    fetchItem(seq);
}

function initScanner() {
    new Html5QrcodeScanner("reader", {
        fps: 10,
        qrbox: { width: 280, height: 120 },
        formatsToSupport: [
            Html5QrcodeSupportedFormats.CODE_128,
            Html5QrcodeSupportedFormats.QR_CODE,
            Html5QrcodeSupportedFormats.EAN_13,
        ],
    }, false).render(onScanSuccess, () => {});
}

function fetchItem(seqNo) {
    hideMsg();
    fetch(`/api/get_item/${seqNo}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) { showError(data.error); return; }
            currentSeqNo = data.sequence_no;
            populateForm(data);
        })
        .catch(() => showError('เกิดข้อผิดพลาดในการเชื่อมต่อ'));
}

function lookupManual() {
    const seq = parseInt(document.getElementById('manual-seq').value.trim(), 10);
    if (isNaN(seq)) { showError('กรุณาพิมพ์เลขลำดับที่'); return; }
    fetchItem(seq);
}

function populateForm(data) {
    const fields = [
        'item_number', 'item_name', 'requisition_item', 'original_item',
        'quantity', 'unit_of_measure', 'issuing_unit', 'requisition_unit',
        'issued_to', 'status', 'responsible_person', 'responsible_phone',
        'transaction_date', 'remarks'
    ];
    fields.forEach(f => {
        const el = document.getElementById('f-' + f);
        if (el) el.value = data[f] ?? '';
    });

    document.getElementById('f-seq-no').textContent = data.sequence_no;
    document.getElementById('verified-badge').classList.toggle('hidden', !data.verified);

    // Show existing item image
    const imgPreview = document.getElementById('item-image-preview');
    if (data.item_image_url) {
        imgPreview.src = data.item_image_url;
        imgPreview.classList.remove('hidden');
    } else {
        imgPreview.classList.add('hidden');
    }

    // Show existing requisition file link
    const reqLink = document.getElementById('requisition-file-link');
    if (data.requisition_file_url) {
        reqLink.href = data.requisition_file_url;
        reqLink.textContent = data.requisition_file;
        reqLink.classList.remove('hidden');
    } else {
        reqLink.classList.add('hidden');
    }

    const info = document.getElementById('last-verified-info');
    info.textContent = data.last_verified_by
        ? `ตรวจสอบล่าสุดโดย: ${data.last_verified_by} เมื่อ ${data.last_verified_at || ''}`
        : 'ยังไม่เคยตรวจสอบ';

    document.getElementById('item-card').classList.remove('hidden');
    loadLogs(data.sequence_no);
}

function verifyItem() {
    if (!currentSeqNo) return;
    fetch(`/api/verify/${currentSeqNo}`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('verified-badge').classList.remove('hidden');
                showSuccess('ยืนยันข้อมูลสำเร็จ');
                loadLogs(currentSeqNo);
            } else {
                showError(data.error || 'เกิดข้อผิดพลาด');
            }
        });
}

function updateItem() {
    if (!currentSeqNo) return;

    const form = new FormData();
    const textFields = [
        'item_number', 'item_name', 'requisition_item', 'original_item',
        'quantity', 'unit_of_measure', 'issuing_unit', 'requisition_unit',
        'issued_to', 'status', 'responsible_person', 'responsible_phone',
        'transaction_date', 'remarks'
    ];
    textFields.forEach(f => {
        const el = document.getElementById('f-' + f);
        if (el) form.append(f, el.value);
    });

    // File uploads
    const reqFile = document.getElementById('f-requisition_file');
    if (reqFile && reqFile.files[0]) form.append('requisition_file', reqFile.files[0]);

    const itemImg = document.getElementById('f-item_image');
    if (itemImg && itemImg.files[0]) form.append('item_image', itemImg.files[0]);

    fetch(`/api/update/${currentSeqNo}`, { method: 'POST', body: form })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('verified-badge').classList.remove('hidden');
                showSuccess('บันทึกข้อมูลสำเร็จ');
                loadLogs(currentSeqNo);
                fetchItem(currentSeqNo);
            } else {
                showError(data.error || 'เกิดข้อผิดพลาด');
            }
        });
}

// Activity log
async function loadLogs(seqNo) {
    const res = await fetch(`/api/item/${seqNo}/logs`);
    const logs = await res.json();
    const tbody = document.getElementById('log-body');

    if (!logs.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="px-3 py-4 text-center text-gray-300">ยังไม่มีประวัติ</td></tr>';
        return;
    }

    const ACTION_COLORS = {
        'สร้างรายการ': 'bg-blue-100 text-blue-700',
        'แก้ไขข้อมูล': 'bg-yellow-100 text-yellow-700',
        'ยืนยันข้อมูล': 'bg-green-100 text-green-700',
        'ลบรายการ':    'bg-red-100 text-red-700',
    };

    tbody.innerHTML = logs.map(log => {
        const color = ACTION_COLORS[log.action] || 'bg-gray-100 text-gray-600';
        return `<tr class="border-t border-gray-100 hover:bg-gray-50">
            <td class="px-3 py-2">
                <span class="inline-block px-2 py-0.5 rounded-full text-xs font-medium ${color}">${log.action}</span>
            </td>
            <td class="px-3 py-2 text-gray-500">${log.action_detail || '-'}</td>
            <td class="px-3 py-2 font-medium">${log.performed_by}</td>
            <td class="px-3 py-2 text-gray-400">${log.performed_at}</td>
        </tr>`;
    }).join('');
}

// Image preview on file select
function previewImage(input, previewId) {
    const file = input.files[0];
    if (!file) return;
    const preview = document.getElementById(previewId);
    preview.src = URL.createObjectURL(file);
    preview.classList.remove('hidden');
}

function showError(msg) {
    const el = document.getElementById('msg');
    el.textContent = msg;
    el.className = 'bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg text-sm';
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 5000);
}
function showSuccess(msg) {
    const el = document.getElementById('msg');
    el.textContent = msg;
    el.className = 'bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg text-sm';
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 3000);
}
function hideMsg() { document.getElementById('msg').classList.add('hidden'); }

document.addEventListener('DOMContentLoaded', initScanner);
document.getElementById('manual-seq').addEventListener('keypress', e => {
    if (e.key === 'Enter') lookupManual();
});
