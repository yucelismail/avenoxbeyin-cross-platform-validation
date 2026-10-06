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

Koşucu sabit commit'leri geçici dizine indirir ve 16 koşu yapar. Sonunda
`sync-validation-....zip` oluşur. ZIP'i paylaşın; yalnız ekran görüntüsü yeterli değildir.
Bu sonuçlar iki fiziksel cihaz testi değil, her platformda iki bağımsız cihaz
kopyasının sentetik entegrasyonudur. Gerçek ağ/cloud sync doğrulanmaz.

## Sonuçları yorumlama

- `passed` / exit 0: ölçülen bütün kontroller geçti.
- `contract_violations` / exit 1: deney çalıştı ve önerilen güvenlik sözleşmesi
  ihlali ölçüldü. Mevcut adaylarda bunun görülmesi bekleniyor.
- `coverage_failed` veya `setup_failed` / exit 2: kurulum/çalıştırma sorunu;
  ürün ihlali olarak yorumlanmaz.

GitHub Actions Linux, macOS ve Windows'ta paketi çalıştırır. Mevcut kodda
kanıtlanan ihlaller nedeniyle workflow kırmızı olabilir; ZIP'teki summary ve vaka
sonuçları incelenmelidir. Testin çalışması ürünün güvenlik kapısını geçtiği anlamına gelmez.

S2/S3/S4/S5/S6/S10'un ilgili alt senaryoları ölçülür. S1 tam korunumu, crash/retry,
CRLF, negatif mutantlar ve bütün senkronizasyon zamanlamaları henüz kapsanmıyor.
#210'un disk otoritesine göre cache onarması kendi başına hata ilan edilmez;
event içeriği değişiminin görünürlüğü önerilen kabul sözleşmesidir.

Eski #198 testi için kökteki `run_validation.py` ve önceki platform yönergeleri
kullanılmaya devam eder.
