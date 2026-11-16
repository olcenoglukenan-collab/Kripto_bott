import os
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from monitoring.feeds import recent_data
from database.store import recent_scans as get_recent_scans
from dotenv import load_dotenv
from market_data.scanner import scan_market
from exchange.binance_public import BinancePublicClient
from database.store import save_scan, recent_scans
from paper_trading import account, open_from_signals, update_positions, reset_account

load_dotenv()
st.set_page_config(page_title='ELİT Crypto Trading AI', page_icon='📈', layout='wide')
st_autorefresh(interval=5000, key='elite_auto_refresh')
st.title('📈 ELİT CRYPTO TRADING AI')
st.caption('OTONOM DEMO • Binance + Bybit + OKX halka açık işlem akışları • Arka plan worker ayrı çalışır')
st.warning('DEMO GÜVENLİĞİ: 100 USDT sanal bakiye. Gerçek emir/API anahtarı/transfer yoktur. Arka plan worker BASLAT.bat ile ayrı süreçte çalışır; tarama otomatik yapılır. Sinyal puanı kazanma olasılığı değildir.')

with st.sidebar:
    st.header('DEMO bot ayarları')
    universe = st.number_input('Tarama evreni', min_value=50, max_value=500, value=int(os.getenv('SCAN_UNIVERSE', '220')), step=10)
    analyze = st.number_input('Detaylı analiz edilecek coin', min_value=5, max_value=100, value=int(os.getenv('ANALYZE_TOP', '30')), step=5)
    min_score = st.slider('Minimum sinyal puanı', 50, 85, 55, 5)
    risk_pct = st.slider('İşlem başına sanal risk (%)', 0.1, 1.0, 0.5, 0.1) / 100
    max_positions = st.slider('Aynı anda açık pozisyon', 1, 5, 3)
    st.caption('Stop: 1,5 × ATR • Hedef: 2R • Sanal kaldıraç etkisi: en fazla 2x notional • Tahmini komisyon: işlem başına %0,04. Funding ve slippage simüle edilmez.')
    run_bot = st.button('🤖 Piyasayı tara + DEMO işle', type='primary', use_container_width=True)
    refresh = st.button('🔄 Açık pozisyonları güncelle', use_container_width=True)
    if st.button('♻️ DEMO hesabını sıfırla', use_container_width=True):
        reset_account(); st.success('DEMO hesabı 100 USDT olarak sıfırlandı.'); st.rerun()

if 'scan_result' not in st.session_state:
    st.session_state.scan_result = None
if 'last_action' not in st.session_state:
    st.session_state.last_action = 'Henüz bot turu çalıştırılmadı.'

if run_bot:
    with st.spinner('Binance public verisi taranıyor, sinyaller değerlendiriliyor ve uygun DEMO pozisyonları açılıyor...'):
        try:
            client = BinancePublicClient()
            result = scan_market(client=client, universe_size=int(universe), analyze_top=int(analyze))
            st.session_state.scan_result = result
            if result['rows']:
                save_scan(result['rows'])
            opened, skipped = open_from_signals(result['rows'], risk_pct=risk_pct, max_positions=max_positions, min_score=min_score)
            st.session_state.last_skipped = skipped[:20]
            # Immediately mark all open positions using current 24h ticker prices.
            tickers = client.ticker_24h()
            prices = {t['symbol']: float(t['lastPrice']) for t in tickers if t.get('lastPrice')}
            closed = update_positions(prices)
            st.session_state.last_action = f"Tarama tamamlandı: {result['analyzed_count']} coin analiz edildi; {len(opened)} yeni DEMO pozisyonu açıldı; {len(closed)} pozisyon kapandı; {len(skipped)} sinyal/pozisyon filtreden geçti."
            st.session_state.scan_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        except Exception as exc:
            st.error(f'Piyasa verisi alınamadı veya DEMO turu tamamlanamadı: {exc}')

if refresh:
    with st.spinner('Açık DEMO pozisyonlarının fiyatları güncelleniyor...'):
        try:
            prices = {t['symbol']: float(t['lastPrice']) for t in BinancePublicClient().ticker_24h() if t.get('lastPrice')}
            closed = update_positions(prices)
            st.session_state.last_action = f"Fiyatlar güncellendi. {len(closed)} pozisyon SL/TP nedeniyle kapandı."
        except Exception as exc:
            st.error(f'Pozisyonlar güncellenemedi: {exc}')

acc, positions, trades = account()
# Open-position unrealized PnL is marked using the last stored mark.
unrealized = sum((p['mark'] - p['entry']) * p['qty'] * (1 if p['side'] == 'LONG' else -1) for p in positions)
equity = acc['balance'] + unrealized
realized_net = sum(float(t['net_pnl']) for t in trades)

st.subheader('💵 Sanal DEMO hesabı')
a,b,c,d,e = st.columns(5)
a.metric('Başlangıç sermayesi', f"{acc['initial_balance']:.2f} USDT")
b.metric('Kullanılabilir bakiye', f"{acc['balance']:.2f} USDT")
c.metric('Açık PnL', f'{unrealized:+.4f} USDT')
d.metric('Toplam öz sermaye', f'{equity:.2f} USDT')
e.metric('Kapanmış işlem net PnL', f'{realized_net:+.4f} USDT')
st.info(st.session_state.last_action)

st.subheader(f'📂 Açık DEMO pozisyonları ({len(positions)})')
if positions:
    pos_df = pd.DataFrame(positions)
    pos_df['unrealized_pnl'] = (pos_df['mark'] - pos_df['entry']) * pos_df['qty'] * pos_df['side'].map({'LONG':1,'SHORT':-1})
    pos_df = pos_df.rename(columns={'symbol':'Coin','side':'Yön','entry':'Giriş','mark':'Son fiyat','qty':'Miktar','stop':'Stop Loss','target':'Take Profit','unrealized_pnl':'Açık PnL (USDT)','opened_at':'Açılış zamanı'})
    st.dataframe(pos_df[['Coin','Yön','Giriş','Son fiyat','Miktar','Stop Loss','Take Profit','Açık PnL (USDT)','Açılış zamanı']], use_container_width=True, hide_index=True)
else:
    st.caption('Henüz açık DEMO pozisyonu yok. Sol menüden “Piyasayı tara + DEMO işle” düğmesine bas.')

st.subheader('📕 Kapanan DEMO işlemleri')
if trades:
    trade_df = pd.DataFrame(trades).rename(columns={'symbol':'Coin','side':'Yön','entry':'Giriş','exit':'Çıkış','qty':'Miktar','gross_pnl':'Brüt PnL','fees':'Toplam komisyon','net_pnl':'Net PnL','reason':'Kapanış nedeni','opened_at':'Açılış','closed_at':'Kapanış'})
    st.dataframe(trade_df[['Coin','Yön','Giriş','Çıkış','Miktar','Brüt PnL','Toplam komisyon','Net PnL','Kapanış nedeni','Açılış','Kapanış']], use_container_width=True, hide_index=True)
else:
    st.caption('İlk pozisyon SL veya TP seviyesine ulaştığında burada görünür.')

result = st.session_state.scan_result
if result:
    c1,c2,c3,c4 = st.columns(4)
    c1.metric('Tarama evreni', result['universe_count']); c2.metric('Detaylı analiz', result['analyzed_count'])
    c3.metric('LONG adayları', sum(r['direction']=='LONG' for r in result['rows']))
    c4.metric('SHORT adayları', sum(r['direction']=='SHORT' for r in result['rows']))
    st.caption(f"Son tarama: {st.session_state.get('scan_time','—')} | Kaynak: Binance public REST")
    df = pd.DataFrame(result['rows'])
    if not df.empty:
        st.subheader('🔎 Teknik fırsat tarayıcı')
        st.dataframe(df.rename(columns={'symbol':'Coin','price':'Fiyat','direction':'Yön','score':'Teknik puan','rsi':'RSI','atr':'ATR','volume_ratio':'Hacim oranı','ema_fast':'EMA 9','ema_slow':'EMA 21','score_note':'Açıklama'}), use_container_width=True, hide_index=True)
    if result['errors']:
        with st.expander(f"Veri hataları ({len(result['errors'])})"):
            st.write('\n'.join(result['errors']))
else:
    st.info('İlk bot turunu başlatmak için sol menüdeki “Piyasayı tara + DEMO işle” düğmesine bas. İnternet bağlantısı gerekir.')

def live_monitor():
    st.divider()
    st.subheader('🌐 Canlı çoklu borsa akışı')
    statuses, whales, recent = recent_data(80)
    scans=get_recent_scans(30)
    if scans:
        st.markdown('**Son otomatik tarama sonuçları**')
        scan_df=pd.DataFrame(scans,columns=['Zaman','Coin','Fiyat','Yön','Puan','RSI'])
        st.dataframe(scan_df,use_container_width=True,hide_index=True)
    if statuses:
        sdf = pd.DataFrame(statuses).rename(columns={'exchange':'Borsa','state':'Bağlantı','last_message':'Son mesaj','detail':'Ayrıntı'})
        st.dataframe(sdf, use_container_width=True, hide_index=True)
    else:
        st.info('Worker henüz feed durumu yazmadı. BASLAT.bat dosyasıyla worker sürecini başlat.')
    st.caption('Büyük gerçekleşmiş borsa işlemleri: 100.000 USDT ve üzeri işlem baskısı. Bunlar cüzdan kimliği bilinen on-chain balina transferleri değildir.')
    if whales:
        wdf=pd.DataFrame(whales).rename(columns={'exchange':'Borsa','symbol':'Coin','side':'Agresör yönü','notional':'İşlem büyüklüğü (USDT)','price':'Fiyat','event_time':'İşlem zamanı'})
        st.dataframe(wdf[['Borsa','Coin','Agresör yönü','İşlem büyüklüğü (USDT)','Fiyat','İşlem zamanı']],use_container_width=True,hide_index=True)
    else:
        st.caption('Henüz 100.000 USDT eşiğini aşan işlem yakalanmadı; bu, balina hareketi olmadığı anlamına gelmez.')
    if recent:
        with st.expander('Son gerçekleşmiş işlemler (Binance / Bybit / OKX)'):
            rdf=pd.DataFrame(recent).rename(columns={'exchange':'Borsa','symbol':'Coin','side':'Yön','price':'Fiyat','qty':'Miktar','notional':'Notional USDT','event_time':'Zaman'})
            st.dataframe(rdf[['Borsa','Coin','Yön','Fiyat','Miktar','Notional USDT','Zaman']],use_container_width=True,hide_index=True)

live_monitor()

st.divider()
st.subheader('Modül durumu')
status_map = {x.get('exchange'): x for x in recent_data(1)[0]}
worker_state = status_map.get('WORKER', {}).get('state', 'Worker durumu henüz alınmadı')
worker_detail = status_map.get('WORKER', {}).get('detail', '')
status = pd.DataFrame([
    ['Binance public REST / 24s ticker','Hazır'], ['USDT perpetual evren filtresi','Hazır'],
    ['5m EMA / RSI / ATR / hacim oranı','Hazır'], ['SQLite tarama günlüğü','Hazır'],
    ['Sanal 100 USDT DEMO hesap','Hazır'], ['DEMO LONG/SHORT pozisyon açma','Sinyal koşullarına bağlı'],
    ['Sanal Stop Loss / Take Profit','Hazır'], ['Açık PnL ve işlem geçmişi','Hazır'],
    ['Bağımsız arka plan worker / otomatik tarama',f'{worker_state} — {worker_detail}'], ['Binance + Bybit + OKX public trade WebSocket','Bağlantı durumunu yukarıda izle'], ['Büyük gerçekleşmiş işlem radarı (100k USDT+)','WebSocket verisi geldikçe etkin'], ['On-chain cüzdan balina transferleri','Harici veri sağlayıcısı/API anahtarı gerekir'],
    ['Haber analiz motoru / Telegram','Henüz yok'], ['LIVE emir / Spot transferi','Bu pakette yok'],
], columns=['Modül','Durum'])
st.dataframe(status, use_container_width=True, hide_index=True)
st.caption('DEMO simülasyonudur. Sanal hesap Windows kullanıcı veri klasöründe kalıcı SQLite veritabanında tutulur; aynı Windows kullanıcı hesabıyla yeniden açıldığında korunur. Gerçek emir göndermez. Otomatik worker için BASLAT.bat açık kalmalı; tarayıcı sekmesini kapatabilirsin. PC uykuya geçerse veri akışı durur. On-chain cüzdan verileri bu pakette yoktur. Komisyon yaklaşık modellenir; funding, slippage ve gerçek likidasyon simülasyonu eksiktir.')
