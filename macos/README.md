# macOS — yalnız kopyala ve yapıştır

Terminal uygulamasını açın. Her kutuyu sırayla tek parça halinde yapıştırın.

## 1. Gerekli araçları kontrol edin

```bash
git --version
python3 --version
```

İki komut da sürüm yazdırıyorsa 2. adıma geçin. `python3` bulunamazsa Homebrew kurup
Python 3.13 yükleyin:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.13
```

Homebrew kurulumunun sonunda ekranda `Next steps` altında verilen PATH komutlarını da
kopyalayıp çalıştırın. Ardından Terminal'i kapatıp yeniden açın.

## 2. Test deposunu indirin

```bash
cd "$HOME/Desktop"
git clone https://github.com/yucelismail/avenoxbeyin-cross-platform-validation.git
cd avenoxbeyin-cross-platform-validation
```

`already exists` hatası alırsanız eski klasörü silmeden farklı ad kullanın:

```bash
cd "$HOME/Desktop"
git clone https://github.com/yucelismail/avenoxbeyin-cross-platform-validation.git avenoxbeyin-validation-new
cd avenoxbeyin-validation-new
```

## 3. Testleri çalıştırın

```bash
bash ./macos/run.sh
```

İşlem birkaç dakika sürebilir. Terminal'i kapatmayın. Son satırlarda
`VALIDATION PASSED` veya `VALIDATION FAILED` yazacaktır. Her iki durumda da sonuç ZIP'i
oluşturulmaya çalışılır.

## 4. Sonucu gönderin

```bash
open -R "$(ls -t validation-result-*.zip | head -n 1)"
```

Finder seçili ZIP dosyasını gösterir. Bu ZIP'i Yücel'e gönderin. ZIP içeriğini
değiştirmeyin ve yalnız ekran görüntüsü göndermeyin.

Bir hata olursa Terminal'deki son metni de kopyalayıp ZIP ile birlikte gönderin.

