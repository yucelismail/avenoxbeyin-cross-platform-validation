# #193 invariant taraması — Faz 1 ve 3

Bu koşucu tarihsel boolean beklentilerini okumaz. Her koşuda son dosyalar ve iki sürecin gerçek sonuçları üzerinden aynı güvenlik ölçütlerini değerlendirir. Önceki matris ve raporlar tarihsel kanıt olarak korunur.

## Güvenlik ölçütleri

| Kod | Ölçüt |
| --- | --- |
| I1 | Eski kartın sabit işareti canlı dosyada veya aylık arşivde bulunur. |
| I2 | Bir süreç `compacted` bildirdiyse taşınabilir tek eski kartın işareti son arşivde bulunur. |
| I3 | İki süreç zamanında biter; istisna, beklenmeyen çıkış veya sonuç durumu yoktur. İzinli durumlar: `compacted`, `conflict`, `needs_rewrite`, `within_limit`. |
| I4 | Dış yazara ait arşiv baytları korunur; Faz 1/3'te dış yazar bulunmadığı için `null`. |

Bu fixture'da üst durum `needs_rewrite` iken `files['Last-Session.md']['status']` alanı `compacted` olabilir. I2 her iki düzeydeki başarı beyanını kontrol eder. Sabit fixture yalnız bir taşınabilir eski kart içerir; çok kartlı veya değişen fixture için her sürecin taşıdığı kartların ayrı takibi gerekir. Tam eski kart, en yeni kart ve önceki arşiv metni ayrıca tanısal olarak denetlenir.

Bir koşunun invariant sonucu yalnız I1–I4'ten gelir. Testin hedef işlemde gerçekten durduğunun kontrolü ayrı `coverage_valid` alanıdır. Hedefe ulaşılamadıysa veya işlem farklıysa koşu güvenlik kanıtı sayılamaz. I3'ün ilerleme sözleşmesi gereği zaman aşımı başarısızlıktır; gözlenen süre ve `fast_finished_before_release` diğer invariant kararlarına girmez.

## Sıralama uzayı

Her aday için yeni ve mevcut arşivle birer tek süreçli iz çıkarılır. Canlı dosya ve aylık arşiv üzerindeki `Path.read_bytes`, `compact._write` ve `Path.unlink` çağrıları izlenir. `_write` içindeki atomik değiştirme tek işlem sayılır. Kilit operasyonları ve başka yollar sayılmaz. Okuma/yazmanın anlamı çağrı yerindeki kaynak satırından adlandırılır; dosya sürümleri işlem numarasıyla eşleştirilmez.

Her izdeki `k=1..N` işleminden **önce** yavaş süreç durdurulur. Hızlı süreç yeni bir `spawn` sürecinde modülü yükleyip kancasız `compact()` çalıştırır. Belirlenen gözlem süresi sonunda yavaş süreç serbest bırakılır. Son dosya hash'leri ve süreç sonuçları geçici dizin silinmeden JSONL'a kaydedilir.

Her k için 16 kombinasyon vardır: aynı/farklı state × aynı/farklı TMPDIR × doğrudan/symlink vault yolu × yeni/mevcut arşiv. Her kombinasyonda ayrıca gerçekten seri çalışan kontrol bulunur. Fixture orijinal reproducer ile aynı 6.140 karakterlik metindir; eski kart 3.074 karakterdir. Tarih `2026-10-03 UTC`, limitler 3.000/8.000 karakterdir.

Her koşuda iki aktör aynı fiziksel vault, canlı dosya ve arşivi paylaşır. `split_state=false` aynı state yolunu; `true`, içerikleri başlangıçta eşit iki ayrı state dizinini verir. `split_tmp=false` aynı geçici dizini; `true`, iki ayrı mevcut dizini verir. Her aktör modül yüklemeden önce `tempfile.tempdir` değerini kendi dizinine ayarlar; bu, farklı `gettempdir()` sonuçlarının kontrollü modelidir. Gerçek container, PrivateTmp veya iki makine çalıştırılmaz. Alias yalnız ikinci aktörün vault yolunu değiştirir; hedef dosyalar aynıdır.

Bu **tek duraklatmalı, sınırlı bir sıralama taramasıdır**. Tek süreçli başlangıç izi rollback/conflict dallarını ziyaret etmeyebilir. Gerçek yarışlarda görülüp duraklatma tohumu olmayan işlem adları `observed_but_not_pause_seeded` alanında gösterilir. Bütün interleaving uzayının tüketildiği veya hiçbir olası sıralamada kayıp olmayacağı iddia edilmez. `exists()` çağrıları ve atomik dosya değiştirme içi syscall'lar protokol gereği ayrı duraklatma noktası değildir.

## Adaylar ve mutantlar

Kaynaklar yerel depolardan tam commit SHA ile `git archive` üzerinden yeni bir koşu dizinine aktarılır. Depodaki çalışma dosyaları değiştirilmez. Kaynak manifesti bütün aktarılmış dosyaların hash'ini, ana commit'i, fixture hash'ini ve koşucu hash'ini içerir. Her koşu yeni çıktı dizini ister; var olan kanıtın üzerine yazmaz.

- v3.7.1: `16af4bc30f0b7e6f6e810e1e1e1ac43e42811ab5`.
- #194: `3279bb2533f96c7101771c99c9286f7ea1845d2f`.
- Upstream #195 hattı (ham koşucu etiketi `pr195`): `1e5b168b13f3779aec8815229616ed35dcd82fa4`. `c6c08f13ad4e5fa1491e1d97e1cb73d2c9678022` üzerine test yolu karşılaştırması ekler ve compact kodu ebeveynle aynıdır. Dış raporda PR numarasının yanında test edilen tam SHA kullanılmalıdır.
- Pozitif referans: yerel `1e5b168` adayında yalnız kilit yolu `Path(vault).resolve() / '.beyin-compact.lock'` yapılır.
- Beş tek değişiklikli mutant: dış kilit, arşiv pre-write karşılaştırması, rollback arşiv sahipliği kontrolü, arşiv yazımından sonraki canlı kontrolü, arşiv yazımından önceki canlı kontrolü ayrı ayrı kaldırılır.

Referansın arşiv sürüm kontrolü tek başına atomik CAS değildir. İşbirliği yapan compact süreçleri için seri çalışma ortak kilitten gelir. Kaynakta son canlı yazımın hemen önünde ayrı bir ek kontrol olmadığı için `mutant_no_live_prewrite`, mevcut `current_live != raw` koşulunu kaldırır. `mutant_no_live_postwrite`, ayrı `path.read_bytes() != raw` korumasını devre dışı bırakır. Okumalar mümkün olduğunda korunur; diff dosyaları `sources/*.patch` içindedir.

Hayatta kalan mutantlar listelenir. Ortak kilit diğer korumaları bu iki aktörlü deneyde gereksiz kılabilir; bu, dış yazar veya çökme altında da gereksiz olduklarının kanıtı değildir.

## Çalıştırma

Benchmark kökünde, Linux/Python 3.12.3 ile:

```bash
BEYIN_TEST_BLOCK_PROBE_SECONDS=1 python3 -B \
  universal-tests/compact-data-loss/invariant_sweep.py \
  --output universal-tests/compact-data-loss/results/invariant-phase1-3-yeni \
  --jobs 4
```

`BEYIN_TEST_READY_TIMEOUT` (varsayılan 20), `BEYIN_TEST_BLOCK_PROBE_SECONDS` (3), `BEYIN_TEST_JOIN_TIMEOUT` (25) ayarlanabilir. Koşular `ProcessPoolExecutor` ile paralel yürütülür; her koşuyu yöneten süreç kendi iki `spawn` aktörünü başlatır ve toplar. Böylece paralel koşular aynı multiprocessing çocuk süreç kayıtlarını paylaşmaz. Bir koşunun dosyaları ve kilitleri diğer koşudan ayrıdır. Gözlem penceresi içinde hızlı aktörün bitmemesi tek başına kilit kanıtı değildir.

Koşucuya ait hedef filtreleme, atomik işlem sınırı, duraklatma konumu, yanlış başarı ve ilerleme denetimleri:

```bash
python3 -B -m unittest discover \
  -s universal-tests/compact-data-loss -p 'test_invariant_sweep.py' -v
```

Üretilen `summary.json`, aday başına ihlal sayısını, ilk ihlal koşulunu, 16 izolasyona göre dağılımı, mutantların öldürülme/hayatta kalma sonucunu ve önceki bağımsız çapa noktalarına uyumu taşır. `cases.jsonl` her koşunun ayrı kaydıdır; `traces.json` başlangıç izlerini, `run.json` kaynak/ortam kimliğini taşır. `REPORT.md` okunabilir tablodur.

Faz 2 (çökme ve yeniden deneme) ve Faz 4 (dış yazar) çalıştırılmaz. Linux symlink deneyi canonical yol eşlemesini sınar; Windows/macOS veya gerçek container/paylaşımlı dosya sistemi doğrulaması sayılmaz.
