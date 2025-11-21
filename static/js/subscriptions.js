// subscriptions.js - DOSYANIN EN BAŞINA EKLENECEK KISIM

// CSRF Token almak için yardımcı fonksiyon
// (Bu, script.js'teki global tanımın yüklenme sırasına takılmamak için eklenmiştir)
function getCSRFToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : ''; 
}

document.addEventListener('DOMContentLoaded', () => {
    try {
        // Ana script.js'in yüklenip yüklenmediğini ve 'translations' nesnesinin var olup olmadığını kontrol et
        if (typeof translations === 'undefined') {
            return; 
        }

        // --- BU SAYFAYA ÖZEL ÇEVİRİ SÖZLÜĞÜ ---
        const promoTranslations = {
            'tr': { 'timer_label': 'BU FİYATLAR İÇİN SON:', 'timer_expired': 'SÜRE DOLDU' },
            'en': { 'timer_label': 'TIME LEFT FOR THESE PRICES:', 'timer_expired': 'TIME\'S UP' },
            'fr': { 'timer_label': 'TEMPS RESTANT POUR CES PRIX:', 'timer_expired': 'EXPIRÉ' },
            'es': { 'timer_label': 'TIEMPO RESTANTE PARA ESTOS PRECIOS:', 'timer_expired': 'EXPIRADO' },
            'ja': { 'timer_label': 'これらの価格の残り時間:', 'timer_expired': '期限切れ' },
            'ko': { 'timer_label': '이 가격의 남은 시간:', 'timer_expired': '만료됨' },
            'zh': { 'timer_label': '这些价格的剩余时间:', 'timer_expired': '已过期' },
            'hi': { 'timer_label': 'इन कीमतों के लिए बचा समय:', 'timer_expired': 'समय समाप्त' }
        };

        const body = document.body;
        const userRole = body.dataset.userRole;
        const cards = document.querySelectorAll('.card');
        
        const currencyMap = {
            'tr': { index: 1, symbol: '₺', position: 'end' }, 'hi': { index: 3, symbol: '₹', position: 'start' },
            'fr': { index: 0, symbol: '€', position: 'end' }, 'es': { index: 0, symbol: '€', position: 'end' },
            'en': { index: 2, symbol: '$', position: 'start' }, 'ja': { index: 2, symbol: '$', position: 'start' },
            'ko': { index: 2, symbol: '$', position: 'start' }, 'zh': { index: 2, symbol: '$', position: 'start' }
        };

        function updateDisplay() {
            const lang = localStorage.getItem('userLanguage') || 'en';
            const currentCurrency = currencyMap[lang] || currencyMap['en'];

            // Genel çevirileri uygula
            document.querySelectorAll('[data-lang-key]').forEach(elem => {
                const key = elem.getAttribute('data-lang-key');
                if (translations[lang] && translations[lang][key]) {
                    if (elem.tagName === 'OPTION' || (elem.tagName !== 'INPUT' && elem.tagName !== 'TEXTAREA')) {
                        elem.textContent = translations[lang][key];
                    }
                }
            });

            // --- SAYAÇ ETİKETİNİ DİLE GÖRE GÜNCELLE ---
            const timerLabels = document.querySelectorAll('.timer-label-text');
            if (timerLabels.length > 0) {
                const labelText = promoTranslations[lang] ? promoTranslations[lang]['timer_label'] : promoTranslations['en']['timer_label'];
                timerLabels.forEach(el => el.textContent = labelText);
            }
            
            // Kartları ve butonları güncelle
            cards.forEach(card => {
                const role = card.dataset.role;
                if (role === 'premium' || role === 'dev') {
                    const dropdown = card.querySelector('.duration-dropdown');
                    if (!dropdown) return;
                    
                    const selectedDuration = dropdown.value;
                    
                    // --- ESKİ VE YENİ FİYAT MANTIĞI ---
                    const priceData = subscriptionData[role].prices[selectedDuration];
                    // Eski fiyat verisi var mı kontrol et
                    const oldPriceData = subscriptionData[role].old_prices ? subscriptionData[role].old_prices[selectedDuration] : null;
                    
                    if (priceData) {
                        const mainPriceValue = priceData[currentCurrency.index];
                        const mainPriceEl = card.querySelector('.main-price');
                        const hourlyPriceEl = card.querySelector('.hourly-price');
                        
                        // Yeni (İndirimli) fiyatı formatla
                        const formattedPrice = currentCurrency.position === 'start' ? 
                            `${currentCurrency.symbol}${mainPriceValue.toLocaleString('de-DE')}` : 
                            `${mainPriceValue.toLocaleString('de-DE')}${currentCurrency.symbol}`;
                        
                        if(mainPriceEl) {
                            if (oldPriceData) {
                                // Eski fiyatı formatla
                                const oldPriceValue = oldPriceData[currentCurrency.index];
                                const formattedOldPrice = currentCurrency.position === 'start' ? 
                                    `${currentCurrency.symbol}${oldPriceValue.toLocaleString('de-DE')}` : 
                                    `${oldPriceValue.toLocaleString('de-DE')}${currentCurrency.symbol}`;
                                
                                // HTML Yapısı: Çizili Eski Fiyat + Parlak Yeni Fiyat
                                mainPriceEl.innerHTML = `
                                    <span class="old-price-strikethrough">${formattedOldPrice}</span>
                                    <span class="new-discounted-price">${formattedPrice}</span>
                                `;
                            } else {
                                // Eski fiyat yoksa normal göster
                                mainPriceEl.textContent = formattedPrice;
                            }
                        }

                        // Saatlik ücret (Yeni fiyat üzerinden hesaplanır)
                        let totalHours = 0;
                        if (selectedDuration === '1w') totalHours = 168;
                        else if (selectedDuration === '1m') totalHours = 720;
                        else if (selectedDuration === '3m') totalHours = 2160;
                        else if (selectedDuration === '5m') totalHours = 3600;
                        else if (selectedDuration === '1y') totalHours = 8760;
                        else if (selectedDuration === 'permanent') totalHours = 43800;
                        
                        if (totalHours > 0 && hourlyPriceEl) {
                             const hourlyPrice = (mainPriceValue / totalHours).toFixed(4);
                             const formattedHourly = currentCurrency.position === 'start' ? `${currentCurrency.symbol}${hourlyPrice}` : `${hourlyPrice}${currentCurrency.symbol}`;
                            hourlyPriceEl.textContent = `${(translations[lang]['hourly'] || 'Hourly')}: ${formattedHourly}`;
                            hourlyPriceEl.style.display = 'block';
                        }
                    }
                }
                
                // Buton mantığını yönet
                const cardFooter = card.querySelector('.card-footer');
                const purchaseBtn = card.querySelector('.purchase-btn');
                if (!cardFooter || !purchaseBtn) return;

                const roleHierarchy = { 'ücretsiz': 0, 'free': 0, 'premium': 1, 'dev': 2 };
                const userLevel = roleHierarchy[userRole] ?? -1;
                const cardLevel = roleHierarchy[role] ?? -1;

                if (userLevel > cardLevel) { 
                    cardFooter.style.display = 'none'; 
                } 
                else if (userLevel === cardLevel) {
                    cardFooter.style.display = 'block';
                    purchaseBtn.disabled = true;
                    purchaseBtn.textContent = (translations[lang]['your_current_plan'] || 'Your Current Plan');
                } else {
                    cardFooter.style.display = 'block';
                    purchaseBtn.disabled = false;
                    purchaseBtn.textContent = (translations[lang]['purchase'] || 'Purchase');
                }
            });
        }

        // Olay dinleyicilerini ekle
        document.querySelectorAll('.duration-dropdown').forEach(dropdown => {
            dropdown.addEventListener('change', updateDisplay);
        });

        // --- SATIN ALMA BUTONU (DOĞRU FİYATI OKUMA) ---
        document.querySelectorAll('.purchase-btn').forEach(button => {
            button.addEventListener('click', async () => {
                // --- KİLİT KONTROLÜ ---
                if (typeof userLimits !== 'undefined' && userLimits.receipt_lockout_until_seconds > 0) {
                    
                    const totalSeconds = userLimits.receipt_lockout_until_seconds;
                    const hours = Math.floor(totalSeconds / 3600);
                    const minutes = Math.floor((totalSeconds % 3600) / 60);
                    
                    // Kalan süreyi formatla (örn: 3s 59dk)
                    let remainingTimeString = "";
                    if (hours > 0) remainingTimeString += `${hours}s `;
                    // Dakikayı her zaman göster, 0 olsa bile (örn: 0dk)
                    remainingTimeString += `${minutes}dk`;

                    // Çeviriyi al ve formatla
                    const errorMsg = getLang('too_many_receipt_attempts', { time: remainingTimeString });
                    
                    showToast(errorMsg, 'error');
                    
                    return; // Fonksiyonu burada durdur, API'yi çağırma
                }
                // --- KİLİT KONTROLÜ SONU ---

                if (button.disabled) return;
                
                const card = button.closest('.card');
                const role = card.dataset.role;
                if (role === 'ücretsiz') return;

                const dropdown = card.querySelector('.duration-dropdown');
                const duration = dropdown.value;
                
                const mainPriceEl = card.querySelector('.main-price');
                
                // *** Fiyatı HTML içinden doğru çekme ***
                let price;
                const newPriceSpan = mainPriceEl.querySelector('.new-discounted-price');
                if (newPriceSpan) {
                    price = newPriceSpan.textContent.trim(); // İndirimli fiyatı al
                } else {
                    price = mainPriceEl.textContent.trim(); // Normal fiyatı al
                }
                
                const originalText = button.textContent;
                button.disabled = true;
                button.textContent = getLang('intent_recorded_redirecting') || 'Niyet kaydediliyor...';
                
                try {
                    const response = await fetch('/create_purchase_intent', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCSRFToken() 
                        },
                        body: JSON.stringify({ 
                            role: role, 
                            duration: duration, 
                            price: price 
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok && data.success) {
                        window.location.href = data.redirect_url;
                    } else {
                        const errorKey = data.error || 'unknown_purchase_error';
                        const translatedError = getLang(errorKey) || 'Niyet oluşturulamadı. Lütfen tekrar deneyin.';
                        
                        showToast(translatedError, 'error');
                        
                        button.textContent = originalText;
                        button.disabled = false;
                    }

                } catch (error) {
                    console.error('Niyet oluşturma hatası:', error);
                    
                    showToast(getLang('server_unreachable_error') || 'Ağ hatası veya sunucuya ulaşılamadı.', 'error');

                    button.textContent = originalText;
                    button.disabled = false;
                }
            });
        });
        
        // Dil değiştirildiğinde ekranı güncelle
        document.addEventListener('languageChanged', () => {
            updateDisplay(); 
        });

        // --- İNDİRİM SAYACI (DİL DESTEKLİ) ---
        function initDiscountTimer() {
            // Premium ve Dev kartlarını seç
            const targetCards = document.querySelectorAll('.card[data-role="premium"], .card[data-role="dev"]');
            if (targetCards.length === 0) return;

            let countDownDate = localStorage.getItem('discountTargetDate');
            if (!countDownDate) {
                const now = new Date().getTime();
                const sevenDaysInMillis = 7 * 24 * 60 * 60 * 1000;
                countDownDate = now + sevenDaysInMillis;
                localStorage.setItem('discountTargetDate', countDownDate);
            }

            const lang = localStorage.getItem('userLanguage') || 'en';
            const labelText = promoTranslations[lang] ? promoTranslations[lang]['timer_label'] : promoTranslations['en']['timer_label'];

            targetCards.forEach(card => {
                if (card.querySelector('.discount-timer-container')) return;

                const cardHeader = card.querySelector('.card-header');
                const timerContainer = document.createElement('div');
                timerContainer.className = 'discount-timer-container';
                
                // span class="timer-label-text" ekledik ki dili değişince bunu bulup güncelleyebilelim
                timerContainer.innerHTML = `
                    <div class="timer-label">
                        <i class="fas fa-bolt"></i> <span class="timer-label-text">${labelText}</span>
                    </div>
                    <div class="timer-digits countdown-display">...</div>
                `;
                cardHeader.parentNode.insertBefore(timerContainer, cardHeader.nextSibling);
            });

            const x = setInterval(function() {
                const now = new Date().getTime();
                const distance = countDownDate - now;
                const displays = document.querySelectorAll('.countdown-display');
                
                // Dil değişiminde anlık güncel metin için (Süre dolduğunda)
                const currentLang = localStorage.getItem('userLanguage') || 'en';
                const expiredText = promoTranslations[currentLang] ? promoTranslations[currentLang]['timer_expired'] : "TIME'S UP";

                if (distance < 0) {
                    localStorage.removeItem('discountTargetDate'); 
                    displays.forEach(d => d.innerHTML = expiredText);
                    clearInterval(x);
                    return;
                }

                const days = Math.floor(distance / (1000 * 60 * 60 * 24));
                const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((distance % (1000 * 60)) / 1000);

                // D, H, M, S harfleri evrensel kalsın
                const timeString = `${days}D ${hours}H ${minutes}M ${seconds}S`;
                displays.forEach(d => d.innerHTML = timeString);

            }, 1000);
        }

        // Sayfa ilk yüklendiğinde içeriği oluştur
        updateDisplay();
        initDiscountTimer();

    } catch (e) {
        // Hata durumunda konsola sadece kritik hatayı yazdır
        console.error('[subscriptions.js] - KRİTİK HATA:', e);
    }
});