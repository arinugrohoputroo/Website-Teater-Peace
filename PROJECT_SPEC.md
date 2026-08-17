# TEATER PEACE — Event Management & Ticketing System

## Phase 1 — Foundation ✅
- Django project structure (modular apps)
- Custom User model (CUSTOMER/STAFF/ADMIN)
- Google OAuth via django-allauth
- Role & permission system (StaffPermission per module)
- Event configuration (database-driven)
- Audit log
- Base UI with Tailwind CSS (mobile-first)
- Panel panitia with sidebar/drawer

## Phase 2 — Participant (Next)
- Participant CRUD
- Customer auto-create on Google login
- Data peserta

## Phase 3 — Ticketing
- Ticket Type management
- Online Order flow
- Offline Sale (panitia)
- Ticket with sequential number (0001-9999)
- QR Code generation

## Phase 4 — Payment
- Payment Method management (BCA, QRIS, etc.)
- Upload bukti transfer
- Verification flow (TERIMA/TOLAK)

## Phase 5 — Check-in
- QR Scanner (browser camera)
- Check-in validation (one-time)
- Rekap check-in

## Phase 6 — Snack
- Snack Session management
- ID Card scan (QR/OCR)
- Claim with duplicate prevention (UNIQUE participant+session)
- Rekap per sesi

## Phase 7 — OCR
- PaddleOCR integration
- Image preprocessing
- ID extraction & database matching

## Phase 8 — Reporting
- Dashboard statistics
- Export Excel/CSV
- Audit log viewer

## Phase 9 — Security & Testing
- Permission testing
- Authentication testing
- Transaction testing
- Mobile testing

---

## Admin Account
- Email: *******
- Dev password: ******

## Setup Google OAuth
1. Buka https://console.cloud.google.com/apis/credentials
2. Buat OAuth 2.0 Client ID (Web application)
3. Authorized JavaScript origins: `http://127.0.0.1:8000`
4. Authorized redirect URIs: `http://127.0.0.1:8000/accounts/google/login/callback/`
5. Isi `GOOGLE_CLIENT_ID` dan `GOOGLE_CLIENT_SECRET` di file `.env`
6. Jalankan: `python manage.py setup_google_oauth`

## Run Development
```bash
cd "d:\Website Teater Peace"
.\.venv\Scripts\activate
python manage.py setup_google_oauth
python manage.py runserver
```
Open http://127.0.0.1:8000

## Test Login
- **Admin**: Login Google dengan `*********` → redirect ke Dashboard
- **Staff**: Login Google dengan email yang sudah didaftarkan Admin → redirect ke Dashboard
- **Customer**: Login Google dengan email apapun → redirect ke Home, akun CUSTOMER otomatis dibuat
