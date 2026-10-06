# Avenox Beyin companion-compact platform doğrulaması

## Yeni: çoklu cihaz sync deneyleri

Receipt bütünlüğü, conflict-copy ve gerçek Git add/add entegrasyon testleri
[sync yönergelerinde](sync/README.md). macOS ve Windows için ayrı çalıştırma
komutları ve GitHub Actions platform matrisi eklendi. Bu paket aşağıdaki
#198 compact doğrulamasından bağımsızdır.

Bu depo #193 veri kaybı düzeltme adayını Windows ve macOS üzerinde aynı şekilde sınar.
Çalıştırıcı resmi `avenoxai/avenoxbeyin` deposunu sabit `9b9aa95` commit'inde geçici
bir klasöre indirir, `candidate.patch` dosyasını uygular ve sentetik vault/state
verileriyle testleri çalıştırır. Kişisel notlara erişmez.

Test sonunda depo kökünde `validation-result-...zip` oluşur. Arkadaşınızın yalnızca
bu ZIP dosyasını size göndermesi yeterlidir.

Yama baytları `.gitattributes` ile Windows satır sonu dönüşümünden korunur. Koşucu ayrıca
eski bir Windows checkout'unda yalnız CRLF dönüşümü olmuşsa bunu hash ile doğrulayıp geçici
LF kopyası kullanır; başka herhangi bir hash farkında çalışmayı reddeder.

- Windows kullanıcısı: [windows/README.md](windows/README.md)
- macOS kullanıcısı: [macos/README.md](macos/README.md)

## Test edilen güvenlik özellikleri

- Aynı vault'a aynı ve farklı state dizinlerinden gelen iki gerçek süreç.
- Her süreç için farklı `TMPDIR`; mümkünse symlink ile görülen geçici dizin.
- Yeni ve mevcut aylık arşiv.
- Eski kartın canlı dosyada veya arşivde tam olarak korunması.
- `compacted` diyen çağrının taşıdığı kartın arşivde bulunması.
- Süreçlerin kilitlenmeden tamamlanması.
- Companion paketinin tamamı, ürün testleri ve yalnız standart kütüphane kontrolü.
- Kilit timeout, açılamama, süreç ölümü sonrası yeniden deneme ve dry-run değişmezliği.

Bu profil gerçek bir NFS/SMB paylaşımını, elektrik kesintisini veya senkronizasyon
aracının kilit dosyasını değiştirmesini doğrulamaz.

## Sonuç ZIP içeriği

- `summary.json`: işletim sistemi, Python, Git, kaynak ve yama kimliği, her komutun sonucu.
- `01-probe.log`: dört çok süreçli veri bütünlüğü senaryosunun JSON çıktısı.
- `02-companion.log`, `03-product.log`, `04-stdlib.log`: unittest çıktıları.
- `patched-diff.stat.txt` ve `patched-status.txt`: uygulanan adayın kısa kimliği.

`summary.json` sonucu `passed`, `tests_failed` veya `setup_failed` olarak sınıflandırır.
Paylaşılan komut ve log yollarındaki kullanıcı profili ile geçici dizin önekleri maskelenir.

## Depoyu GitHub'a koyacak kişi için

README'lerde şu adres kullanılıyor:

`https://github.com/yucelismail/avenoxbeyin-cross-platform-validation.git`

Depoyu başka adla açarsanız iki platform README'sindeki bu adresi değiştirin. GitHub'a
yüklemeden önce `candidate.patch.sha256` ile yamanın hash'ini doğrulayın. Sonuç ZIP'leri
`.gitignore` kapsamındadır; test sonucu içerecek yeni bir commit gerekmez.

## Published evidence

The source-matched invariant, crash/retry, Linux, macOS, and Windows evidence for the candidate is published in [`evidence/`](evidence/README.md).
