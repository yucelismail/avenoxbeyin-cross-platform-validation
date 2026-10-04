# #193 invariant taraması — Faz 1 ve 3

Her aday kendi tek süreçli izinde görülen işlem sınırlarında duraklatıldı. Her sınır 16 izolasyon kombinasyonunda denendi; ayrıca her kombinasyonda seri kontrol koşuldu.

| Aday | Koşu | İhlalli koşu | İlk ihlal işlemi | Invariant |
| --- | ---: | ---: | --- | --- |
| reference | 112 | 0 | — | — |
| mutant_no_lock | 112 | 16 | archive_write | I1, I2 |

## İzolasyon başına ilk ihlal

Hücreler ilk ihlal işlemidir; `—` bu kapsamda ihlal görülmediğini belirtir. Yol sütununda alias, ikinci aktörün aynı vault’a symlink üzerinden erişmesidir.

| Arşiv | state | TMPDIR | Yol | reference | mutant_no_lock |
| --- | --- | --- | --- | --- | --- |
| yok | aynı | aynı | doğrudan | — | archive_write |
| yok | aynı | aynı | alias | — | archive_write |
| yok | aynı | farklı | doğrudan | — | archive_write |
| yok | aynı | farklı | alias | — | archive_write |
| yok | farklı | aynı | doğrudan | — | archive_write |
| yok | farklı | aynı | alias | — | archive_write |
| yok | farklı | farklı | doğrudan | — | archive_write |
| yok | farklı | farklı | alias | — | archive_write |
| var | aynı | aynı | doğrudan | — | archive_write |
| var | aynı | aynı | alias | — | archive_write |
| var | aynı | farklı | doğrudan | — | archive_write |
| var | aynı | farklı | alias | — | archive_write |
| var | farklı | aynı | doğrudan | — | archive_write |
| var | farklı | aynı | alias | — | archive_write |
| var | farklı | farklı | doğrudan | — | archive_write |
| var | farklı | farklı | alias | — | archive_write |

Mutant sonuçları:

| Mutant | Sonuç | Öldüren koşu sayısı | İlk koşu |
| --- | --- | ---: | --- |
| mutant_no_lock | killed | 16 | archive-new__state-shared__tmp-shared__vault-direct__k03-archive_write |

Hayatta kalanlar: .

Hayatta kalmak, korumanın genel olarak gereksiz olduğunu kanıtlamaz. Bu taramada dış yazar yoktur ve mutantların dördü ortak vault kilidini korur. I4 bu yüzden uygulanmaz (`null`).

Tarama tek bir işlem öncesinde duraklatır; bütün interleaving uzayının model kontrolü değildir. Tek süreçli başlangıç izi conflict/rollback dallarını ziyaret etmeyebilir. Çalışırken görülüp duraklatma tohumu olmayan işlemler özet JSON içinde ayrıca listelenir.

Faz 2 (çökme/yeniden deneme), Faz 4 (dış yazar), Windows ve macOS bu koşuda çalıştırılmadı. Linux symlink testi canonical yol birleştirmesini sınar; macOS doğrulaması sayılmaz.

Referansın arşiv kontrolü PR195’teki ayrı oku/karşılaştır/yaz dizisidir; atomik CAS değildir. Canlı yazım öncesi bağımsız ek kontrol bulunmadığından son mutant, mevcut `current_live != raw` pre-write koşulunu kaldırır. Yazım sonrası kontrol ayrı mutanttır.

Özet: [summary.json](summary.json). Ayrıntılı koşular: [cases.jsonl](cases.jsonl). İzler: [traces.json](traces.json). Kaynaklar ve mutant diff’leri: `sources/`.
