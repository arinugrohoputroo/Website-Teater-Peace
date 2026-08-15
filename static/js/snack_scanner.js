(function () {
    const cfg = window.SNACK_SCANNER || {};
    const sessionSelect = document.getElementById('session-select');
    const statusText = document.getElementById('status-text');
    const statusSub = document.getElementById('status-sub');
    const cameraFrame = document.getElementById('camera-frame');
    const cameraStatusBox = document.getElementById('camera-status-box');
    const cameraStatusIcon = document.getElementById('camera-status-icon');
    const cameraStatusTitle = document.getElementById('camera-status-title');
    const cameraStatusDetail = document.getElementById('camera-status-detail');
    const cameraStatusHint = document.getElementById('camera-status-hint');
    const cameraIndicator = document.getElementById('camera-indicator');
    const btnStart = document.getElementById('btn-start-camera');
    const btnStop = document.getElementById('btn-stop-camera');
    const btnTorch = document.getElementById('btn-torch');
    const torchUnsupported = document.getElementById('torch-unsupported');

    let html5QrCode = null;
    let scanning = false;
    let processing = false;
    let cooldownUntil = 0;
    let lastToken = '';
    let torchOn = false;
    let videoTrack = null;

    const COOLDOWN_MS = 2500;
    const FRAME_STATES = ['state-idle', 'state-scanning', 'state-processing', 'state-success', 'state-duplicate', 'state-error'];
    const BOX_STATES = ['box-scanning', 'box-processing', 'box-success', 'box-duplicate', 'box-error'];

    function setStatus(main, sub) {
        statusText.textContent = main;
        statusSub.textContent = sub ? `Status: ${sub}` : '';
    }

    function setCameraOverlay(state, icon, title, detail) {
        FRAME_STATES.forEach((s) => cameraFrame.classList.remove(s));
        BOX_STATES.forEach((s) => cameraStatusBox.classList.remove(s));

        if (state === 'idle') {
            cameraFrame.classList.add('state-idle');
            cameraStatusBox.classList.add('hidden');
            cameraStatusHint.classList.add('hidden');
            return;
        }

        cameraFrame.classList.add(`state-${state}`);
        cameraStatusBox.classList.remove('hidden');
        cameraStatusBox.classList.add(`box-${state}`);
        cameraStatusIcon.textContent = icon || '';
        cameraStatusTitle.textContent = title || '';
        cameraStatusDetail.textContent = detail || '';

        if (state === 'scanning') {
            cameraStatusHint.classList.remove('hidden');
        } else {
            cameraStatusHint.classList.add('hidden');
        }
    }

    function splitName(name) {
        if (!name) return { title: '-', subtitle: '' };
        const parts = name.split(',');
        return {
            title: parts[0].trim(),
            subtitle: parts.slice(1).join(',').trim(),
        };
    }

    async function submitToken(token) {
        const sessionId = sessionSelect.value;
        if (!sessionId) {
            setCameraOverlay('error', '✕', 'PILIH SESI', 'Pilih sesi snack terlebih dahulu.');
            setStatus('Pilih sesi snack terlebih dahulu.', 'ERROR');
            return;
        }
        processing = true;
        cooldownUntil = Date.now() + COOLDOWN_MS;
        setCameraOverlay('processing', '⏳', 'MEMPROSES', 'Validasi QR token...');
        setStatus('Memproses...', 'PROCESSING');

        try {
            const res = await fetch(cfg.processUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': cfg.csrfToken,
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    qr_token: token,
                }),
            });
            const data = await res.json();
            handleResponse(data);
        } catch (err) {
            setCameraOverlay('error', '✕', 'KONEKSI GAGAL', 'Silakan coba lagi.');
            setStatus('Koneksi ke server gagal.', 'ERROR');
        } finally {
            setTimeout(() => {
                if (scanning) {
                    setCameraOverlay('scanning', '📷', 'SCANNING', 'Arahkan QR ID Card ke kamera');
                    setStatus('Menunggu QR berikutnya...', 'SCANNING');
                } else {
                    setCameraOverlay('idle');
                }
                processing = false;
                lastToken = '';
            }, COOLDOWN_MS);
        }
    }

    function handleResponse(data) {
        const sessionName = sessionSelect.options[sessionSelect.selectedIndex]
            ? sessionSelect.options[sessionSelect.selectedIndex].text
            : (data.session || '');
        const name = data.member ? data.member.name : '';
        const parts = splitName(name);
        const memberId = data.member ? data.member.id : '';

        if (data.status === 'approved') {
            const detail = [parts.subtitle, memberId, sessionName, 'Snack berhasil diambil'].filter(Boolean).join(' · ');
            setCameraOverlay('success', '✓', parts.title, detail);
            setStatus('Snack berhasil diambil.', 'SUCCESS');
            return;
        }
        if (data.status === 'already_claimed') {
            const detail = [name, sessionName, `Diambil: ${data.claimed_at || '-'}`].filter(Boolean).join(' · ');
            setCameraOverlay('duplicate', '⚠', 'SUDAH MENGAMBIL', detail);
            setStatus('Sudah mengambil snack.', 'DUPLICATE');
            return;
        }
        if (data.status === 'inactive') {
            setCameraOverlay('error', '✕', 'TIDAK AKTIF', 'ID panitia ini tidak aktif.');
            setStatus('ID panitia tidak aktif.', 'INACTIVE');
            return;
        }
        setCameraOverlay('error', '✕', 'QR TIDAK DIKENAL', 'QR tidak terdaftar sebagai ID Card panitia.');
        setStatus('QR tidak dikenal.', 'UNKNOWN');
    }

    async function onScanSuccess(decodedText) {
        const token = (decodedText || '').trim();
        if (!token) return;
        if (processing) return;
        if (Date.now() < cooldownUntil) return;
        if (token === lastToken) return;
        lastToken = token;
        await submitToken(token);
    }

    function detectTorchSupport() {
        try {
            const video = document.querySelector('#qr-reader video');
            if (!video || !video.srcObject) {
                torchUnsupported.classList.remove('hidden');
                return;
            }
            const track = video.srcObject.getVideoTracks()[0];
            videoTrack = track;
            const caps = track.getCapabilities ? track.getCapabilities() : {};
            if (caps && caps.torch) {
                btnTorch.classList.remove('hidden');
                torchUnsupported.classList.add('hidden');
            } else {
                btnTorch.classList.add('hidden');
                torchUnsupported.classList.remove('hidden');
            }
        } catch (e) {
            btnTorch.classList.add('hidden');
            torchUnsupported.classList.remove('hidden');
        }
    }

    async function toggleTorch() {
        if (!videoTrack) return;
        try {
            torchOn = !torchOn;
            await videoTrack.applyConstraints({ advanced: [{ torch: torchOn }] });
            btnTorch.textContent = torchOn ? '🔦 Matikan Lampu' : '🔦 Nyalakan Lampu';
        } catch (e) {
            torchUnsupported.classList.remove('hidden');
            btnTorch.classList.add('hidden');
        }
    }

    async function startCamera() {
        if (!sessionSelect.value) {
            setCameraOverlay('error', '✕', 'PILIH SESI', 'Pilih sesi snack terlebih dahulu.');
            setStatus('Pilih sesi snack terlebih dahulu.', 'ERROR');
            return;
        }
        if (!window.Html5Qrcode) {
            setCameraOverlay('error', '✕', 'SCANNER ERROR', 'Library QR scanner gagal dimuat.');
            setStatus('Library QR scanner gagal dimuat.', 'ERROR');
            return;
        }
        try {
            html5QrCode = new Html5Qrcode('qr-reader');
            await html5QrCode.start(
                { facingMode: 'environment' },
                {
                    fps: 10,
                    qrbox: function (viewfinderWidth, viewfinderHeight) {
                        const size = Math.floor(Math.min(viewfinderWidth, viewfinderHeight) * 0.7);
                        return { width: size, height: size };
                    },
                    aspectRatio: 1.0,
                },
                onScanSuccess,
                function () {}
            );
            scanning = true;
            btnStart.disabled = true;
            btnStop.disabled = false;
            cameraIndicator.textContent = 'Kamera Aktif';
            cameraIndicator.className = 'text-xs px-2 py-1 rounded-full bg-green-700 text-green-100';
            setCameraOverlay('scanning', '📷', 'SCANNING', 'Arahkan QR ID Card ke kamera');
            setStatus('Arahkan QR ID Card ke kamera', 'SCANNING');
            setTimeout(detectTorchSupport, 800);
        } catch (err) {
            const msg = String(err && err.message ? err.message : err);
            if (/NotAllowedError|Permission|denied/i.test(msg)) {
                setCameraOverlay('error', '✕', 'IZIN DITOLAK', 'Aktifkan Camera Permission pada browser.');
                setStatus('Izin kamera ditolak.', 'ERROR');
            } else {
                setCameraOverlay('error', '✕', 'KAMERA GAGAL', 'Pastikan browser memiliki izin kamera.');
                setStatus('Kamera tidak dapat diakses.', 'ERROR');
            }
        }
    }

    async function stopCamera() {
        scanning = false;
        torchOn = false;
        videoTrack = null;
        btnTorch.classList.add('hidden');
        if (html5QrCode) {
            try {
                const state = html5QrCode.getState && html5QrCode.getState();
                const isScanning = state === 2 || state === 1 || (typeof Html5QrcodeScannerState !== 'undefined' && state === Html5QrcodeScannerState.SCANNING);
                if (isScanning) {
                    await html5QrCode.stop();
                }
            } catch (e) {}
            try { html5QrCode.clear(); } catch (e) {}
            html5QrCode = null;
        }
        btnStart.disabled = false;
        btnStop.disabled = true;
        cameraIndicator.textContent = 'Kamera Off';
        cameraIndicator.className = 'text-xs px-2 py-1 rounded-full bg-gray-700 text-gray-300';
        setCameraOverlay('idle');
        setStatus('Kamera dimatikan.', 'OFF');
    }

    btnStart.addEventListener('click', startCamera);
    btnStop.addEventListener('click', stopCamera);
    btnTorch.addEventListener('click', toggleTorch);
    window.addEventListener('beforeunload', () => { stopCamera(); });
})();
