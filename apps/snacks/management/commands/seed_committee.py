from django.core.management.base import BaseCommand

from apps.snacks.models import CommitteeMember, generate_qr_token, normalize_committee_name

COMMITTEE_NAMES = [
    'Rohmad Pujiono, S.Psi., M.Si',
    'Ari Nugroho Putro, S.Pd',
    'Salwa Salsabela S.Ling',
    'Fera Dyah Ayu, S.Pi',
    'Desiyana Salsa Bela, S.E',
    'Magista Wulandari, S.Pd',
    "Ma'ruf Setiawan, S.Pd",
    'Rizqi Farid Maulana, M.Pd',
    'Alifuddin Moonthousand',
    'Muhamad Roy Ananda Saputra, S.T',
    'Selamet Rama Novendra',
    'Muhammad Naufal Vahrio Andilala',
    'Alyatul Musfirotun',
    "M. Rif'an Jawahiruddin, S.Pd.",
    'Erif Enanda, S.Ds',
    'Fadlur Rohman, S.Sn., M.Pd',
    'Discka Tri Ayu Amara',
    'Kirana Anggi Rahayu',
    'Aprilia Ayu Wulandari',
    'Feby Anggi, S.E.',
    'Ayu Putri Sanggiri',
    'Nirmala Setyani',
    'Nurul Hidayah, S.Pi',
    'Difi Safitri, S.Ak',
    'Via Melinda Putri',
    'Muhammad Abu Jamroh, S.S',
    'Muhammad Arip Yusron',
    'Muhammad Hafidz Zakaria, S.M',
    'Ferli Ariawan',
    'Amanda',
    'Sahrul',
]


def _unique_token():
    for _ in range(20):
        token = generate_qr_token()
        if not CommitteeMember.objects.filter(qr_token=token).exists():
            return token
    raise RuntimeError('Gagal membuat qr_token unik.')


class Command(BaseCommand):
    help = 'Seed 31 anggota panitia + QR token (idempotent).'

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for index, name in enumerate(COMMITTEE_NAMES, start=1):
            code = f'P{index:03d}'
            normalized = normalize_committee_name(name)
            member = CommitteeMember.objects.filter(name=name).first()
            if member is None:
                member = CommitteeMember(
                    name=name,
                    normalized_name=normalized,
                    member_code=code,
                    qr_token=_unique_token(),
                    active=True,
                )
                member.save()
                created += 1
                continue

            fields = []
            if not member.member_code:
                member.member_code = code
                fields.append('member_code')
            if not member.qr_token:
                member.qr_token = _unique_token()
                fields.append('qr_token')
            if member.normalized_name != normalized:
                member.normalized_name = normalized
                fields.append('normalized_name')
            if not member.active:
                member.active = True
                fields.append('active')
            if fields:
                fields.append('updated_at')
                member.save(update_fields=fields)
                updated += 1

        total = CommitteeMember.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'Seed selesai. Created: {created}, Updated: {updated}, Total: {total}'
        ))
