import base64
from io import BytesIO

import qrcode
from django.db import IntegrityError, transaction

from apps.core.models import log_action

from .models import CommitteeMember, SnackClaim


def generate_committee_qr(member, box_size=10, border=4):
    """Generate QR image from member.qr_token only (never name)."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(member.qr_token)
    qr.make(fit=True)
    return qr.make_image(fill_color='black', back_color='white')


def committee_qr_data_uri(member, box_size=10, border=4):
    img = generate_committee_qr(member, box_size=box_size, border=border)
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


@transaction.atomic
def process_qr_snack_scan(*, qr_token, session, operator):
    token = (qr_token or '').strip().upper()
    if not token:
        return {
            'success': False,
            'status': 'unknown',
            'message': 'QR Code ini tidak terdaftar sebagai ID Card panitia.',
        }

    member = CommitteeMember.objects.filter(qr_token__iexact=token).first()
    if not member:
        return {
            'success': False,
            'status': 'unknown',
            'message': 'QR Code ini tidak terdaftar sebagai ID Card panitia.',
        }

    if not member.active:
        return {
            'success': False,
            'status': 'inactive',
            'message': 'ID panitia ini tidak aktif.',
            'member': member,
        }

    if not session.active:
        return {
            'success': False,
            'status': 'invalid_session',
            'message': 'Sesi snack tidak aktif.',
            'member': member,
        }

    existing = (
        SnackClaim.objects.select_related('operator', 'session')
        .filter(committee_member=member, session=session)
        .first()
    )
    if existing:
        return {
            'success': False,
            'status': 'already_claimed',
            'message': 'Panitia sudah mengambil snack pada session ini',
            'member': member,
            'claim': existing,
            'session': session,
        }

    try:
        claim = SnackClaim.objects.create(
            committee_member=member,
            session=session,
            operator=operator,
            detection_method=SnackClaim.DetectionMethod.QR,
            qr_token_used=member.qr_token,
        )
    except IntegrityError:
        existing = (
            SnackClaim.objects.select_related('operator', 'session')
            .filter(committee_member=member, session=session)
            .first()
        )
        return {
            'success': False,
            'status': 'already_claimed',
            'message': 'Panitia sudah mengambil snack pada session ini',
            'member': member,
            'claim': existing,
            'session': session,
        }

    log_action(
        operator,
        'SNACK_CLAIM',
        'snacks',
        member.member_code,
        f'{member.name} claim snack {session.name}',
        metadata={
            'session': session.name,
            'method': 'QR',
            'member_code': member.member_code,
            'qr_token': member.qr_token,
        },
    )
    return {
        'success': True,
        'status': 'approved',
        'message': 'Snack berhasil diambil',
        'member': member,
        'claim': claim,
        'session': session,
    }


def serialize_qr_scan_result(result):
    member = result.get('member')
    claim = result.get('claim')
    session = result.get('session')
    payload = {
        'success': result['success'],
        'status': result['status'],
        'message': result['message'],
    }
    if member:
        payload['member'] = {
            'name': member.name,
            'id': member.member_code,
            'member_code': member.member_code,
        }
    if session:
        payload['session'] = session.name
    if claim:
        payload['claimed_at'] = claim.claimed_at.strftime('%H:%M:%S')
        payload['operator'] = claim.operator.name if claim.operator_id else ''
    return payload
