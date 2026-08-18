import os
import shutil
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.ticketing.models import ShowScript, TicketType


class Command(BaseCommand):
    help = 'Seed data naskah pertunjukan teater dan waktu pertunjukan season.'

    def handle(self, *args, **options):
        # Copy poster images from static/posters to MEDIA_ROOT/posters
        poster_src_dir = os.path.join(settings.BASE_DIR, 'static', 'posters')
        poster_dst_dir = os.path.join(settings.MEDIA_ROOT, 'posters')
        os.makedirs(poster_dst_dir, exist_ok=True)

        if os.path.exists(poster_src_dir):
            for f in os.listdir(poster_src_dir):
                src_file = os.path.join(poster_src_dir, f)
                if os.path.isfile(src_file):
                    try:
                        shutil.copy2(src_file, os.path.join(poster_dst_dir, f))
                    except Exception:
                        pass

        naskah_data = [
            {
                'title': 'Mengukir Mimpi',
                'synopsis': (
                    'Menceritakan Tri Indah Pertiwi, gadis Jepara yang bercita-cita menjadi pengukir meski '
                    'ditentang ayahnya yang menginginkan ia menjadi PNS. Dengan dukungan kakaknya, Tri tetap '
                    'memperjuangkan mimpinya di bidang seni ukir. Setelah melalui perjuangan panjang dan tantangan '
                    'selama tujuh tahun, ia berhasil menjadi pengukir profesional dan membawa karya ukir Jepara ke '
                    'dunia, sekaligus membuktikan bahwa mimpi layak diperjuangkan.'
                ),
                'cast': 'Evin Sesillia Jati sebagai Tri Indah Ayu Pertiwi',
                'director': 'R. Pujiono',
                'production_by': 'Teater Peace & Peace Forum',
                'poster': 'posters/mengukir-mimpi.png',
                'order': 1,
            },
            {
                'title': 'Terlambat',
                'synopsis': (
                    'Mira seorang siswi SMA biasa tidak mencolok, tidak menarik, bahkan tidak banyak yang menyadari '
                    'kehadirannya, hanya Silvi teman satu satunya yang dimilikinya. Sampai datang geng pembully yang '
                    'entah bagaimana membencinya tanpa alasan yang jelas, cacian dan kekerasan mereka lakukan pada Mira. '
                    'Dan Mira harus menghadapi sakit bertahun-tahun yang tak kunjung sembuh. Akankah Mira bisa bertahan di sekolah sampai akhir?'
                ),
                'cast': (
                    'Mira diperankan oleh Talita tiara wati\n'
                    'Silvi diperankan oleh Saskia ayu Permata sari\n'
                    'Aeryn diperankan oleh Dinda ainur Rahma\n'
                    'Jessica diperankan oleh Christy carol lientjewas\n'
                    'Elsa diperankan oleh Vania arnesya pradindya'
                ),
                'director': 'R. Pujiono',
                'production_by': 'Teater Peace & Peace Forum',
                'poster': 'posters/terlambat.jpg',
                'order': 2,
            },
            {
                'title': 'Semuria',
                'synopsis': (
                    'Legimah, penjaga sederhana Hutan Wisata Desa Semuria, terkejut saat warung-warung di kawasan '
                    'wisata dirusak. Ia kemudian bertekad mencari pelaku hingga ke Pulau Mandalika, dibantu Kang '
                    'Bimantara dan Lestari. Di sana, mereka bertemu Baskoro yang mengaku melakukan perusakan bukan untuk '
                    'merusak, melainkan untuk menyadarkan masyarakat tentang pentingnya menjaga kelestarian Gunung Muria.\n\n'
                    'Baskoro menegaskan bahwa tanpa kepedulian lingkungan, alam akan rusak dan mengancam kehidupan manusia. '
                    'Gunung Muria bukan hanya sumber kehidupan, tetapi juga menyimpan nilai sejarah, budaya, dan kearifan lokal yang harus dijaga.\n\n'
                    'Di akhir cerita, Legimah menyadari bahwa semua kejadian tersebut hanyalah mimpi, namun menjadi peringatan penting bahwa menjaga alam adalah tanggung jawab bersama.'
                ),
                'cast': 'Adzra Aqilla Muhibba Sebagai Legimah',
                'director': 'R. Pujiono',
                'production_by': 'Teater Peace & Peace Forum',
                'poster': 'posters/semuria.png',
                'order': 3,
            },
            {
                'title': 'Sulung',
                'synopsis': (
                    'Mengisahkan seorang kakak bernama Kasih yang harus mengorbankan cita citanya menjadi seorang guru, '
                    'Demi adiknya yang bernama Laras. Sang adik yang terkenal sebagai murid teladan hingga banyak memenangkan '
                    'perlombaan, Justru berbanding terbalik dengan sang kakak yang berprofesi sebagai seorang pelacur. Semua berawal baik-baik saja, '
                    'Laras menyembunyikan profesi asli kakaknya demi citra baiknya di sekolah. Hingga suatu hari disaat teman-teman Laras yaitu Karin dan Dinda '
                    'bermain dikamar Laras, Dinda mendapatkan file video yang membuat Dinda dan Karin kecewa sampai tidak percaya lagi dengan Laras. '
                    'Setelah kejadian itu Laras malu dan bahkan marah kepada sang kakak, Yang tanpa disadari oleh Laras bahwa file video itu hanya kesalahpahaman. '
                    'Sang Kakak lakukan apapun itu demi menghidupi adiknya ia pernah menjadi pemulung, tukang parkir, dan yang terakhir merelakan dirinya menjadi seorang pelacur. '
                    'Setelah Kakak memberitahu fakta yang begitu menyakitkan tentang kehidupan Ayah dan Ibunya kepada Laras yang membuat Laras kaget, Hingga membuat Laras semakin muak '
                    'dan memiliki niat untuk mengakhiri hidupnya agar ia tidak menjadi beban kakaknya lagi. Namun niat Laras mengakhiri hidupnya menjadi rasa bersalah.'
                ),
                'cast': (
                    '1. Kayla Febriani Amandita sebagai ( Kasih )\n'
                    '2. Nawira sebagai ( Laras )\n'
                    '3. Ceria Bintang Maulina sebagai ( Karin )\n'
                    '4. Indira Widasari sebagai ( Dinda )'
                ),
                'director': 'R. Pujiono',
                'production_by': 'Teater Peace & Peace Forum',
                'poster': 'posters/sulung.jpg',
                'order': 4,
            },
            {
                'title': 'Jago Kluruk',
                'synopsis': (
                    'Jago Kluruk bercerita tentang keluarga sederhana yang hidup dalam keterbatasan. Namun, Pakne lebih sayang ayam jagonya daripada keluarganya, '
                    'sementara Wagisan, anak mereka, terus menuntut berbagai keinginannya demi gengsi di hadapan pacarnya, Deajeng Tulkiyem. Demi memenuhi janji kepada keluarga, '
                    'Pakne mempertaruhkan harapan lewat adu jago, tetapi kekalahan justru membuatnya kehilangan akal sehat. Konflik semakin kacau ketika Wagisan ditinggalkan Tulkiyem '
                    'hingga akhirnya ikut kehilangan kendali. Mampukah Bune menghadapi tingkah suami dan anaknya?'
                ),
                'cast': (
                    'Pakne diperankan oleh Alifudin Moonthousand\n'
                    'Bukne diperankan oleh Fera Dyah Ayu\n'
                    'Wagisan diperankan oleh Maruf Setiawan\n'
                    'Tulkiyem diperankan oleh Erif Enanda'
                ),
                'director': 'R. Pujiono',
                'production_by': 'Teater Peace & Peace Forum',
                'poster': 'posters/jago-kluruk.jpg',
                'order': 5,
            },
        ]

        naskah_objects = {}
        for item in naskah_data:
            script, created = ShowScript.objects.update_or_create(
                title=item['title'],
                defaults={
                    'synopsis': item['synopsis'],
                    'cast': item['cast'],
                    'director': item['director'],
                    'production_by': item['production_by'],
                    'poster': item['poster'],
                    'order': item['order'],
                }
            )
            naskah_objects[item['title']] = script
            action = 'Created' if created else 'Updated'
            self.stdout.write(f"{action} Naskah: {script.title}")

        season_configs = [
            {
                'name_contains': 'Season 1',
                'time': '08.30 - 11.30',
                'naskah': ['Mengukir Mimpi', 'Terlambat', 'Semuria', 'Sulung'],
            },
            {
                'name_contains': 'Season 2',
                'time': '13.30 - 16.30',
                'naskah': ['Mengukir Mimpi', 'Terlambat', 'Semuria', 'Sulung', 'Jago Kluruk'],
            },
            {
                'name_contains': 'Season 3',
                'time': '18.30 - 21.30',
                'naskah': ['Mengukir Mimpi', 'Terlambat', 'Semuria', 'Sulung', 'Jago Kluruk'],
            },
        ]

        for s_cfg in season_configs:
            seasons = TicketType.objects.filter(name__icontains=s_cfg['name_contains'])
            for season in seasons:
                season.show_time = s_cfg['time']
                season.save(update_fields=['show_time'])
                assigned_scripts = [naskah_objects[title] for title in s_cfg['naskah'] if title in naskah_objects]
                season.naskah_list.set(assigned_scripts)
                self.stdout.write(f"Updated {season.name} (Time: {season.show_time}, Naskah: {len(assigned_scripts)})")

        self.stdout.write(self.style.SUCCESS("Seed Naskah & Season berhasil diselesaikan."))
