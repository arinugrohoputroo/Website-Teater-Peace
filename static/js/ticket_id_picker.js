(function () {
    function initTicketIdPicker(root) {
        if (!root || root.dataset.initialized === '1') return;
        root.dataset.initialized = '1';

        const apiUrl = root.dataset.apiUrl;
        const maxQty = root.dataset.maxQty ? parseInt(root.dataset.maxQty, 10) : null;
        const textarea = document.querySelector(root.dataset.textarea || '[name="ticket_numbers"]');
        const countEl = document.querySelector(root.dataset.countEl || '#ticket-count');
        const searchInput = root.querySelector('#id-picker-search');
        const listEl = root.querySelector('#id-picker-list');
        const statusEl = root.querySelector('#id-picker-status');
        const totalEl = root.querySelector('#id-picker-count');
        const moreBtn = root.querySelector('#id-picker-more');
        const emptyEl = root.querySelector('#id-picker-empty');

        if (!apiUrl || !textarea || !listEl) return;

        let offset = listEl.querySelectorAll('.id-chip').length;
        let total = parseInt(totalEl ? totalEl.textContent : '0', 10) || 0;
        let hasMore = moreBtn && !moreBtn.classList.contains('hidden');
        let search = '';
        let loading = false;

        function parseIds(raw) {
            return raw.replace(/\n/g, ',').split(',').map(v => v.trim()).filter(Boolean);
        }

        function selectedSet() {
            return new Set(parseIds(textarea.value));
        }

        function updateChipStates() {
            const selected = selectedSet();
            listEl.querySelectorAll('.id-chip').forEach((chip) => {
                const id = chip.dataset.ticket;
                if (selected.has(id)) {
                    chip.classList.add('is-selected', 'bg-gold-300', 'border-gold-500', 'text-navy-900', 'ring-2', 'ring-gold-400/50');
                    chip.classList.remove('bg-navy-50', 'border-navy-100', 'text-navy-700');
                } else {
                    chip.classList.remove('is-selected', 'bg-gold-300', 'border-gold-500', 'text-navy-900', 'ring-2', 'ring-gold-400/50');
                    chip.classList.add('bg-navy-50', 'border-navy-100', 'text-navy-700');
                }
            });
        }

        function notifyChange() {
            updateChipStates();
            if (countEl) countEl.textContent = String(parseIds(textarea.value).length);
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        }

        function bindChip(chip) {
            chip.addEventListener('click', () => {
                const id = chip.dataset.ticket;
                const ids = parseIds(textarea.value);
                const idx = ids.indexOf(id);
                if (idx >= 0) {
                    ids.splice(idx, 1);
                } else {
                    if (maxQty !== null && ids.length >= maxQty) return;
                    ids.push(id);
                }
                textarea.value = ids.join(', ');
                notifyChange();
            });
        }

        function appendIds(ids) {
            if (emptyEl) emptyEl.remove();
            ids.forEach((id) => {
                if (listEl.querySelector('[data-ticket="' + id + '"]')) return;
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.dataset.ticket = id;
                btn.className = 'id-chip px-2.5 py-1 rounded-lg bg-navy-50 hover:bg-gold-100 border border-navy-100 text-xs font-mono text-navy-700 transition-colors';
                btn.textContent = id;
                bindChip(btn);
                listEl.appendChild(btn);
            });
            updateChipStates();
        }

        function updateStatus(shown) {
            if (!statusEl) return;
            if (search) {
                statusEl.textContent = 'Hasil pencarian: ' + shown + ' dari ' + total;
            } else {
                statusEl.textContent = 'Menampilkan ' + shown + ' dari ' + total;
            }
        }

        async function fetchIds(reset) {
            if (loading) return;
            loading = true;
            if (moreBtn) moreBtn.disabled = true;
            try {
                if (reset) {
                    offset = 0;
                    listEl.innerHTML = '';
                }
                const params = new URLSearchParams({
                    offset: String(offset),
                    limit: '200',
                    q: search,
                });
                const res = await fetch(apiUrl + '?' + params.toString(), {
                    headers: { 'Accept': 'application/json' },
                });
                if (!res.ok) throw new Error('Gagal memuat ID');
                const data = await res.json();
                total = data.total;
                hasMore = data.has_more;
                if (totalEl) totalEl.textContent = String(total);
                appendIds(data.ids || []);
                offset += (data.ids || []).length;
                updateStatus(listEl.querySelectorAll('.id-chip').length);
                if (moreBtn) {
                    moreBtn.classList.toggle('hidden', !hasMore);
                    moreBtn.disabled = false;
                }
                if (!listEl.querySelector('.id-chip') && !listEl.querySelector('#id-picker-empty')) {
                    const p = document.createElement('p');
                    p.id = 'id-picker-empty';
                    p.className = 'text-sm text-navy-400';
                    p.textContent = search ? 'ID tidak ditemukan.' : 'Tidak ada ID tersedia.';
                    listEl.appendChild(p);
                }
            } catch (err) {
                if (statusEl) statusEl.textContent = 'Gagal memuat ID. Coba lagi.';
            } finally {
                loading = false;
                if (moreBtn && hasMore) moreBtn.disabled = false;
            }
        }

        listEl.querySelectorAll('.id-chip').forEach(bindChip);
        updateChipStates();

        if (moreBtn) {
            moreBtn.addEventListener('click', () => fetchIds(false));
        }

        let searchTimer;
        if (searchInput) {
            searchInput.addEventListener('input', () => {
                clearTimeout(searchTimer);
                searchTimer = setTimeout(() => {
                    search = searchInput.value.trim();
                    fetchIds(true);
                }, 300);
            });
        }

        textarea.addEventListener('input', updateChipStates);
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('#ticket-id-picker').forEach(initTicketIdPicker);
    });
})();
