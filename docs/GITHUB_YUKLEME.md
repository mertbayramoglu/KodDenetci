# GitHub'a yükleme

## Önce karar verin
1. **Kurum politikası:** Kod iş zamanında/ekipmanıyla yazıldıysa herkese açık depo için gerekli onayı alın. Emin değilseniz **Private** başlayın; sonra public yapabilirsiniz.
2. **Hassas veri:** `veri/` klasörü ve `*.db` dosyaları taranan projelerden alıntı içerir. `.gitignore` bunları dışarıda tutar; yükleme betiği de sızıntı varsa durur.
3. **Depo adı önerisi:** `kod-denetci` (açıklama: "Yerel statik kod denetimi ve LLM düzeltme prompt'u üretici").

## Kolay yol (önerilen)
GitHub'da **boş** bir depo oluşturun (README/LICENSE eklemeden), sonra proje klasöründe:

```bat
tools\github_hazirla.bat
```
Betik sırasıyla: CI dosyasını yerine taşır, testleri çalıştırır, `git init` + `git add` yapar, `veri/` ve `.db` sızıntısını denetler,
eklenecek dosyaları gösterir, onayınızla commit eder ve depo adresini girerseniz `push` eder.

## Elle yol
```bat
mkdir .github\workflows
move docs\ci.yml.txt .github\workflows\ci.yml
git init
git symbolic-ref HEAD refs/heads/main
git add .
git status
git commit -m "Kod Denetci 1.1.0"
git remote add origin https://github.com/mertbayramoglu/KodDenetci.git
git push -u origin main
git tag v1.1.0
git push origin v1.1.0
```
GitHub CLI ile: `gh repo create kod-denetci --private --source . --push`

## Sonrası
- **Actions** sekmesinde CI'ın (Windows + Ubuntu, Python 3.9 ve 3.13) yeşil olduğunu doğrulayın.
- **Releases → Draft a new release**: etiket `v1.1.0`; kaynak zip'i yeterlidir. İmzasız `.exe` yüklemeyin.
- Depo ayarlarında **Secret scanning** ve **Private vulnerability reporting** özelliklerini açın.
- Kimlik bilgisi/token hiçbir dosyaya yazmayın; push için Git Credential Manager kullanın.
