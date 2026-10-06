# Çoklu cihaz sync — ilk kabul deneyleri

Bu paket #198 compact testlerinden ayrıdır. İki sentetik vault ve ayrı SQLite
state kullanır; kullanıcının Beyin kasasını veya global hook ayarlarını değiştirmez.
Git senaryosu iki dalda aynı event için farklı receipt commit eder, gerçek add/add
çatışmasını doğrular ve B seçilerek çözümden sonra sync'i ölçer.

Sabit adaylar: main `9b9aa95848b7dbee6ba13415c3615671d4445862`,
PR #210 `bf7f993ffc90085cd5c430098e537bab72ddf8f6`.

Git ve Python 3.12+ gerekir. Depoyu yeni indirin veya mevcut kopyada `git pull`
çalıştırın. Ardından depo kökünde:

macOS:

```sh
python3 run_sync_validation.py
```

Windows PowerShell:

```powershell
py -3 run_sync_validation.py
```

Koşucu sabit commit'leri geçici dizine indirir ve 96 probe koşusu ve düzeltilmiş adayın 49 sync birim testini yapar. Sonunda
`sync-validation-....zip` oluşur. ZIP'i paylaşın; yalnız ekran görüntüsü yeterli değildir.
Bu sonuçlar iki fiziksel cihaz testi değil, her platformda iki bağımsız cihaz
kopyasının sentetik entegrasyonudur. Gerçek ağ/cloud sync doğrulanmaz.

## Sonuçları yorumlama

- `fixed_candidate_passed` / exit 0: düzeltilmiş adayın 12 probe koşusu ve 49 sync testi geçti; eski main/#210 başarısızlıkları raporda karşılaştırma olarak kalır.
- `fixed_candidate_failed` / exit 1: düzeltilmiş aday probe veya sync birim testi kapısını geçemedi.
- `coverage_failed` veya `setup_failed` / exit 2: kurulum/çalıştırma sorunu;
  ürün ihlali olarak yorumlanmaz.

GitHub Actions Linux, macOS ve Windows'ta paketi çalıştırır. Kabul kapısı `fixed` adayına uygulanır. main ve pr210 tarihsel negatif karşılaştırmalardır; sonuçları silinmez veya başarılıya çevrilmez. Probe tek başına çalıştırıldığında aynı 0/1/2 davranışını korur.

S2/S3/S4/S5/S6/S10'un ilgili alt senaryoları ölçülür. S1 tam korunumu, crash/retry,
CRLF, negatif mutantlar ve bütün senkronizasyon zamanlamaları henüz kapsanmıyor.
#210'un disk otoritesine göre cache onarması kendi başına hata ilan edilmez;
event içeriği değişiminin görünürlüğü önerilen kabul sözleşmesidir.

Eski #198 testi için kökteki `run_validation.py` ve önceki platform yönergeleri
kullanılmaya devam eder.

## İlk ürün düzeltme adayı

`receipt-visibility.patch`, sabit #210 tabanına hash doğrulamasıyla uygulanır. Aynı event
kimliğinin payload'ı değiştiğinde SQLite'taki eski kayıt ve diskteki yeni dosya korunur;
`degraded` ve kaynak/event kimliği/iki payload hash'i bildirilir. Sessiz UPDATE yapılmaz.
Tekrar sync uyarıyı sürdürür. Çakışma çözülene kadar projeksiyon eski SQLite kaydını
korur; bu temiz mutabakat iddiası değildir. Bu ihtiyatlı politika #210'un otomatik
cache mutabakatını değiştirir ve bakımcı değerlendirmesi gerektirir.

Yama deneysel adaydır; upstream merge veya kullanıcı vault'una kurulum yapılmadı.
Uyarıyı onaylama/onarım CLI'ı, state sıfırlamasında eski payload'ın kalıcılığı ve
tam korunumu ve crash/CRLF senaryoları henüz tamamlanmadı. Bu sürüm S1–S10'un tamamını
geçmiş bir üretim çözümü olarak sunulmaz.

## İkinci adım: sıcak tarama önbelleği

İki ek senaryo var: `inplace_changed` ve `inplace_same`. Önce receipt klasörü
yaşlandırılır ve temiz sync çalıştırılır. Sonra mevcut dosyaya yerinde yazılır;
klasör `mtime_ns` değerinin değişmediği koşucu tarafından doğrulanır. Değişen
payload uyarılmalı, aynı payload temiz başarıyla devam etmelidir.

İlk aday `f9c22b4` değişen payload senaryosunu iki tekrarda kaçırdı (S3/S4).
Yeni aday `_scan_receipts` içindeki yalnız klasör zamanına dayanan erken dönüşü
kaldırır; eski state içindeki `receipt_scan_signature` değerlerini kullanmaz.
Her sync receipt içeriklerini yeniden okur. Maliyet receipt sayısı/içerik boyutuyla
artar; ilerideki optimizasyon bu güvenlik özelliklerini korumalıdır.

## Üçüncü adım: negatif kontroller

Normal aday ve tarihsel karşılaştırmalara ek olarak beş mutant ayrı geçici
checkout'ta koşar: `silent_receipt_update`, `skip_receipt_rescan`,
`no_conflict_copy_filter`, `always_succeeded`, `delete_quarantined_note_copy`.
Son ikisiyle birlikte conflict-copy mutantları **note** korumasını değiştirir;
receipt hash-ad filtresinin bütün biçimlerini mutasyonla kapsadığımız iddia edilmez.

Her mutant altı senaryoda ikişer kez çalışır. Gate yalnız normal aday geçtiğinde
ve her mutantın hedef invariant'ı iki tekrarda exit 1 ile ihlal ettiğinde geçer.
Kurulum hatası, timeout, eksik vaka veya bozuk mutation anchor başarı sayılmaz.
Ham JSONL ve kaynak hash'li `mutants.json` ZIP içindedir.

Bu adım ürün koduna yeni bir özellik eklemez; test aracının hatayı yakalama
duyarlılığını doğrular. Crash/CRLF ve tam korunumu henüz kapsamaz.
