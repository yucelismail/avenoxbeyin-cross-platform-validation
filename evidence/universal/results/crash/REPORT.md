# #193 invariant taraması — Faz 1 ve 3

Her aday kendi tek süreçli izinde görülen işlem sınırlarında duraklatıldı. Her sınır 16 izolasyon kombinasyonunda denendi; ayrıca her kombinasyonda seri kontrol koşuldu.

| Aday | Koşu | İhlalli koşu | İlk ihlal işlemi | Invariant |
| --- | ---: | ---: | --- | --- |
| reference | 112 | 0 | — | — |

## İzolasyon başına ilk ihlal

Hücreler ilk ihlal işlemidir; `—` bu kapsamda ihlal görülmediğini belirtir. Yol sütununda alias, ikinci aktörün aynı vault’a symlink üzerinden erişmesidir.

| Arşiv | state | TMPDIR | Yol | reference |
| --- | --- | --- | --- | --- |
| yok | aynı | aynı | doğrudan | — |
| yok | aynı | aynı | alias | — |
| yok | aynı | farklı | doğrudan | — |
| yok | aynı | farklı | alias | — |
| yok | farklı | aynı | doğrudan | — |
| yok | farklı | aynı | alias | — |
| yok | farklı | farklı | doğrudan | — |
| yok | farklı | farklı | alias | — |
| var | aynı | aynı | doğrudan | — |
| var | aynı | aynı | alias | — |
| var | aynı | farklı | doğrudan | — |
| var | aynı | farklı | alias | — |
| var | farklı | aynı | doğrudan | — |
| var | farklı | aynı | alias | — |
| var | farklı | farklı | doğrudan | — |
| var | farklı | farklı | alias | — |

Mutant sonuçları:

| Mutant | Sonuç | Öldüren koşu sayısı | İlk koşu |
| --- | --- | ---: | --- |

Hayatta kalanlar: .

Hayatta kalmak, korumanın genel olarak gereksiz olduğunu kanıtlamaz. Bu taramada dış yazar yoktur ve mutantların dördü ortak vault kilidini korur. I4 bu yüzden uygulanmaz (`null`).

Tarama tek bir işlem öncesinde duraklatır; bütün interleaving uzayının model kontrolü değildir. Tek süreçli başlangıç izi conflict/rollback dallarını ziyaret etmeyebilir. Çalışırken görülüp duraklatma tohumu olmayan işlemler özet JSON içinde ayrıca listelenir.

Faz 2 (çökme/yeniden deneme), Faz 4 (dış yazar), Windows ve macOS bu koşuda çalıştırılmadı. Linux symlink testi canonical yol birleştirmesini sınar; macOS doğrulaması sayılmaz.

Referansın arşiv kontrolü PR195’teki ayrı oku/karşılaştır/yaz dizisidir; atomik CAS değildir. Canlı yazım öncesi bağımsız ek kontrol bulunmadığından son mutant, mevcut `current_live != raw` pre-write koşulunu kaldırır. Yazım sonrası kontrol ayrı mutanttır.

Özet: [summary.json](summary.json). Ayrıntılı koşular: [cases.jsonl](cases.jsonl). İzler: [traces.json](traces.json). Kaynaklar ve mutant diff’leri: `sources/`.
