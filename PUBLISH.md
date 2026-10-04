# Test deposunu GitHub'a yükleme

Bu depo yerelde hazırlandı; henüz commit veya push yapılmadı. Önce GitHub web sitesinde
`yucelismail/avenoxbeyin-cross-platform-validation` adlı boş bir **public** depo oluşturun.
README, `.gitignore` veya lisans ekleme seçeneklerini işaretlemeyin.

Yerel Git kimliğini kontrol edin. `EMAIL` yerine GitHub hesabınızda doğrulanmış adresi
veya GitHub noreply adresinizi yazın:

```bash
cd /home/yucel/avenoxbeyin-cross-platform-validation
git config --local user.name "İsmail Yücel"
git config --local user.email "EMAIL"
git var GIT_AUTHOR_IDENT
```

Dosyaları inceleyin ve commit'i kendiniz oluşturun:

```bash
git status --short
git diff --no-index /dev/null README.md || true
sha256sum -c candidate.patch.sha256
git add .gitignore README.md PUBLISH.md candidate.patch candidate.patch.sha256 compact_probe.py run_validation.py windows macos
git diff --cached --check
git diff --cached --stat
git commit -m "test: add Windows and macOS compact race validation"
```

GitHub deposunu bağlayıp gönderin:

```bash
git remote add origin https://github.com/yucelismail/avenoxbeyin-cross-platform-validation.git
git remote -v
git push -u origin main
```

GitHub kullanıcı adı veya depo adı farklıysa önce README dosyalarındaki clone adreslerini
ve yukarıdaki remote adresini aynı değere güncelleyin. Arkadaşlarınıza depo ana sayfasının
bağlantısını ve kendi işletim sistemlerine ait README dosyasını gönderin.

