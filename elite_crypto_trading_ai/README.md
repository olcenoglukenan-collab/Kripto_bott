# ELİT Crypto Trading AI — Multi-Exchange DEMO v3

## Güvenlik
- Yalnızca public piyasa verisi kullanır; API anahtarı istemez.
- Gerçek emir, gerçek hesap erişimi ve para transferi kodu yoktur.
- 100 USDT sanal paper-trading hesabı kullanır.
- Büyük işlem radarı, bilinen cüzdan kimliği değildir; borsalarda gerçekleşen büyük işlemleri gösterir.

## v3 yenilikleri
- Ayrı `worker.py` süreci: dashboard kapanıp açılsa da worker çalışmaya devam eder.
- Binance USD-M, Bybit Linear ve OKX Spot public trade WebSocket akışları.
- 220'ye kadar likit sembol için akış aboneliği.
- 60 saniyede bir otomatik teknik tarama ve DEMO sinyal değerlendirmesi.
- WebSocket fiyatlarıyla açık DEMO pozisyonlarını arka planda güncelleme.
- 100.000 USDT ve üzeri gerçekleşmiş işlem baskısı için büyük işlem radarı.
- Dashboard 5 saniyede bir tüm metrikleri ve tarama sonuçlarını kendi kendine günceller.
- WebSocket kopunca otomatik yeniden bağlanma.

## Windows 11 kurulum
1. Python 3.12 64-bit kurulu olmalı.
2. `KUR.bat` çalıştırılır.
3. `BASLAT.bat` çalıştırılır. Bu, ayrı arka plan worker'ını ve Streamlit panelini başlatır.
4. Panel: http://localhost:8501
5. `DURDUR.bat` worker'a durma işareti verir. Panel terminalini kapatmak için Ctrl+C kullanılır.

## Önemli çalışma notları
- Dashboard sekmesini kapatabilirsiniz; worker ayrı süreçte kalır. `BASLAT.bat` açılan worker penceresi/işlemi çalışır durumda kalmalıdır.
- Bilgisayar uykuya geçerse veya kapanırsa yerel worker durur. Windows güç ayarlarında uyku kapatılmalı; gerçek 7/24 için VPS gerekir.
- Tarama/teknik indikatörler hâlâ Binance Futures mum verisi kullanır. Bybit ve OKX bu sürümde canlı gerçekleşmiş işlem akışı ve büyük işlem radarı için eklenmiştir; bütün borsalardaki bütün coin/ürünlerin tam kapsamlı taraması değildir.
- On-chain cüzdan transferleri (borsa giriş/çıkışları) için ayrı bir veri sağlayıcısı/API aboneliği gerekir; bu sürümde yer almaz. Büyük borsa işlemlerini on-chain balina transferi olarak yorumlamayın.
- Haber motoru, Telegram, gerçek order-book spoofing analizi, funding/OI çapraz-borsa birleştirmesi, VPS servis kurulumu ve LIVE emir/transfer özellikleri tamamlanmış değildir.
- Bu bir araştırma DEMO'sudur; kârlılık veya kazanma oranı garantisi vermez.


## v4 düzeltmeleri
- Worker başlangıcındaki log klasörü sıralama hatası düzeltildi; worker artık log klasörünü dosyayı açmadan önce oluşturur.
- Worker durumunu ve son tarama özetini dashboard'da gösterir.
- Otomatik işlem filtresi varsayılan 55 puana ayarlandı; açılmayan sinyallerin nedenleri loglarda gösterilir.
- DEMO hesabı, piyasa olayları ve tarama kayıtları proje klasöründen bağımsız Windows kullanıcı veri dizinine taşındı: `%LOCALAPPDATA%\\ELITCryptoTradingAI\\data`.
- Aynı Windows kullanıcı hesabıyla V4'ü yeniden açınca sanal bakiye ve geçmiş korunur. Sıfırlama düğmesi kayıtları siler.

## Bilgisayar kapatılırsa
- SQLite kayıtları diskte kalır; bilgisayarı kapatmak bakiyeyi kendi başına sıfırlamaz.
- Bilgisayar kapalı/uykudayken worker çalışmaz, yeni piyasa verisi alamaz ve stop/target tetiklerini anlık işleyemez. Açıldıktan sonra güncel fiyatla yeniden devam eder.
- Tam 7/24 takip için botun sürekli açık bir VPS/sunucuda çalışması gerekir.
- Dashboard sekmesini kapatabilirsiniz; worker terminali/işlemi açık kalmalıdır. Bilgisayarı yeniden başlatınca `BASLAT.bat` dosyasını yeniden çalıştırın.
