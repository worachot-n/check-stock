// Fetch field suggestions from server and populate all <datalist> elements
const SUGGESTION_FIELDS = [
    'original_item', 'requisition_item', 'item_name',
    'issuing_unit', 'requisition_unit', 'issued_to',
    'supply_control_section', 'supply_borrowing_unit',
    'status', 'supply_type', 'responsible_person', 'responsible_phone',
];

async function loadSuggestions() {
    try {
        const res = await fetch('/api/field_suggestions');
        if (!res.ok) return;
        const data = await res.json();
        SUGGESTION_FIELDS.forEach(field => {
            const values = data[field] || [];
            document.querySelectorAll(`datalist[data-field="${field}"]`).forEach(dl => {
                dl.innerHTML = values.map(v => `<option value="${v.replace(/"/g, '&quot;')}"></option>`).join('');
            });
        });
    } catch (_) {}
}

document.addEventListener('DOMContentLoaded', loadSuggestions);
