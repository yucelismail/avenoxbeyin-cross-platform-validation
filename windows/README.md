# Windows — yalnız kopyala ve yapıştır

Windows 10 veya 11 gerekir. PowerShell'i normal kullanıcı olarak açın. Her kutuyu sırayla
tek parça halinde yapıştırın.

## 1. Git ve Python'u kurun

```powershell
winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
winget install --id Python.Python.3.13 -e --source winget --accept-package-agreements --accept-source-agreements
```

Kurulum bitince PowerShell penceresini kapatıp yeniden açın.

## 2. Test deposunu indirin

```powershell
Set-Location "$HOME\Desktop"
git clone https://github.com/yucelismail/avenoxbeyin-cross-platform-validation.git
Set-Location .\avenoxbeyin-cross-platform-validation
```

`already exists` hatası alırsanız önce eski klasörü silmek yerine farklı bir klasör adıyla
indirin:

```powershell
Set-Location "$HOME\Desktop"
git clone https://github.com/yucelismail/avenoxbeyin-cross-platform-validation.git avenoxbeyin-validation-new
Set-Location .\avenoxbeyin-validation-new
```

## 3. Testleri çalıştırın

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\windows\run.ps1
```

İşlem birkaç dakika sürebilir. Pencereyi kapatmayın. Son satırlarda
`VALIDATION PASSED` veya `VALIDATION FAILED` yazacaktır. Her iki durumda da sonuç ZIP'i
oluşturulmaya çalışılır.

## 4. Sonucu gönderin

```powershell
Get-ChildItem .\validation-result-*.zip | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object { explorer.exe /select,"$($_.FullName)" }
```

Dosya Gezgini seçili ZIP dosyasını gösterir. Bu ZIP'i testleri değerlendiren bakımcıyla paylaşın. ZIP içeriğini
değiştirmeyin ve yalnız ekran görüntüsü göndermeyin.

Bir hata olursa PowerShell'deki son metni de kopyalayıp ZIP ile birlikte gönderin.
