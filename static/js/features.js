// features.js
document.addEventListener('DOMContentLoaded', () => {
    // --- Gerekli Elementler ---
    const featureToggles = document.querySelectorAll('.feature-card:not(.locked) .switch input');
    const selectedList = document.getElementById('selected-features-list');
    const startButton = document.getElementById('start-features-btn');
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    // YENİ: Antenna linkini metadan oku
    const antennaLink = document.querySelector('meta[name="antenna-link"]').getAttribute('content');
    
    // YENİ: Dil, Tema ve Tepsi Elementleri
    const body = document.body;
    const langSelector = document.querySelector('.language-selector');
    const langCurrentBtn = document.querySelector('.lang-current');
    const langOptions = document.querySelectorAll('.lang-option');
    const themeToggleButton = document.getElementById('themeToggleButton');
    const featuresMainContent = document.querySelector('.features-main-content'); // Kaydırma alanı
    const bottomActionArea = document.getElementById('bottomActionArea'); // Sabit tepsi
    let isTrayVisible = false;

    // YENİ: Yönlendirme Modal Elementleri
    const redirectModal = document.getElementById('subscriptionRedirectModal');
    const redirectModalContinue = document.getElementById('modalRedirectContinue');
    const redirectModalBack = document.getElementById('modalRedirectBack');
    const lockedCards = document.querySelectorAll('.feature-card.locked .lock-overlay');

    // YENİ: Dil Çevirileri (GÜNCELLENDİ)
    const translations = {
        tr: {
            config_features: "CONFIG ÖZELLİKLERİ",
            purchase_to_unlock: "Kilidi Açmak için Satın Al",
            selected_features_title: "Seçtiğiniz Özellikler",
            start_button: "İNDİR",
            alert_no_features: "Lütfen en az bir özellik seçin!",
            config_fail: "İstek gönderilirken bir hata oluştu.",
            creating_countdown: "Oluşturuluyor... {s}",
            lang_native: "Türkçe",
            redirect_to_subs_prompt: "Abonelik sayfasına yönlendirileceksiniz", // YENİ
            modal_back: "Geri", // YENİ
            modal_continue: "Devam Et" // YENİ
        },
        en: {
            config_features: "CONFIG FEATURES",
            purchase_to_unlock: "Purchase to Unlock",
            selected_features_title: "Your Selected Features",
            start_button: "DOWNLOAD",
            alert_no_features: "Please select at least one feature!",
            config_fail: "An error occurred while sending the request.",
            creating_countdown: "Creating... {s}",
            lang_native: "English",
            redirect_to_subs_prompt: "You will be redirected to the subscriptions page", // YENİ
            modal_back: "Back", // YENİ
            modal_continue: "Continue" // YENİ
        },
        fr: {
            config_features: "FONCTIONNALİTÉS CONFIG",
            purchase_to_unlock: "Acheter pour déverrouiller",
            selected_features_title: "Vos fonctionnalités sélectionnées",
            start_button: "TÉLÉCHARGER",
            alert_no_features: "Veuillez sélectionner au moins une fonctionnalité !",
            config_fail: "Une erreur s'est produite lors de l'envoi de la demande.",
            creating_countdown: "Création... {s}",
            lang_native: "Français",
            redirect_to_subs_prompt: "Vous serez redirigé vers la page des abonnements", // YENİ
            modal_back: "Retour", // YENİ
            modal_continue: "Continuer" // YENİ
        },
        es: {
            config_features: "FUNCIONES DE CONFIGURACIÓN",
            purchase_to_unlock: "Comprar para desbloquear",
            selected_features_title: "Sus funciones seleccionadas",
            start_button: "DESCARGAR",
            alert_no_features: "¡Por favor, seleccione al menos una función!",
            config_fail: "Se produjo un error al enviar la solicitud.",
            creating_countdown: "Creando... {s}",
            lang_native: "Español",
            redirect_to_subs_prompt: "Será redirigido a la página de suscripciones", // YENİ
            modal_back: "Atrás", // YENİ
            modal_continue: "Continuar" // YENİ
        },
        ja: {
            config_features: "設定機能",
            purchase_to_unlock: "購入してロック解除",
            selected_features_title: "選択した機能",
            start_button: "ダウンロード",
            alert_no_features: "少なくとも1つの機能を選択してください！",
            config_fail: "リクエストの送信中にエラーが発生しました。",
            creating_countdown: "作成中... {s}",
            lang_native: "日本語",
            redirect_to_subs_prompt: "サブスクリプションページにリダイレクトされます", // YENİ
            modal_back: "戻る", // YENİ
            modal_continue: "続行" // YENİ
        },
        ko: {
            config_features: "설정 기능",
            purchase_to_unlock: "구매하여 잠금 해제",
            selected_features_title: "선택한 기능",
            start_button: "다운로드",
            alert_no_features: "적어도 하나의 기능을 선택하십시오!",
            config_fail: "요청을 보내는 중 오류가 발생했습니다.",
            creating_countdown: "생성 중... {s}",
            lang_native: "한국어",
            redirect_to_subs_prompt: "구독 페이지로 리디렉션됩니다", // YENİ
            modal_back: "뒤로", // YENİ
            modal_continue: "계속" // YENİ
        },
        zh: {
            config_features: "配置功能",
            purchase_to_unlock: "购买以解锁",
            selected_features_title: "您选择的功能",
            start_button: "下载",
            alert_no_features: "请至少选择一项功能！",
            config_fail: "发送请求时出错。",
            creating_countdown: "创建中... {s}",
            lang_native: "中文",
            redirect_to_subs_prompt: "您将被重定向到订阅页面", // YENİ
            modal_back: "返回", // YENİ
            modal_continue: "继续" // YENİ
        },
        hi: {
            config_features: "कॉन्फ़िगरेशन सुविधाएँ",
            purchase_to_unlock: "अनलॉक करने के लिए खरीदें",
            selected_features_title: "आपकी चयनित सुविधाएँ",
            start_button: "डाउनलोड करें",
            alert_no_features: "कृपया कम से कम एक सुविधा चुनें!",
            config_fail: "अनुरोध भेजते समय एक त्रुटि हुई।",
            creating_countdown: "बनाया जा रहा है... {s}",
            lang_native: "हिन्दी",
            redirect_to_subs_prompt: "आपको सदस्यता पृष्ठ पर पुनः निर्देशित किया जाएगा", // YENİ
            modal_back: "वापस", // YENİ
            modal_continue: "जारी रखें" // YENİ
        }
    };

    // --- YENİ FONKSİYONLAR: Dil ve Tema ---
    function getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }

    function applyTranslations(lang) {
        const langPack = translations[lang] || translations.tr;
        document.querySelectorAll('[data-lang-key]').forEach(el => {
            const key = el.getAttribute('data-lang-key');
            if (langPack[key]) {
                el.textContent = langPack[key];
            }
        });
        if (langCurrentBtn) {
            langCurrentBtn.querySelector('img').src = `/static/images/${lang}.png`;
        }
    }

    async function changeLanguage(lang) {
        if (!translations[lang]) lang = 'tr';
        localStorage.setItem('userLanguage', lang);
        applyTranslations(lang);
        // Sunucudaki dil tercihini de güncelle
        try {
            await fetch('/update_language', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ language: lang })
            });
        } catch (error) {
            console.error("Dil sunucuya güncellenirken hata:", error);
        }
    }

    function loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark-theme';
        body.className = savedTheme;
        updateThemeIcon(savedTheme);
    }

    function updateThemeIcon(theme) {
        if (themeToggleButton) {
            themeToggleButton.querySelector('i').className = theme === 'dark-theme' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }
    
    // --- ANA MANTIK: Alt Tepsiyi Gösterme/Gizleme ve İçerik Güncelleme ---
    
    // Alt tepsiyi görünür/gizli hale getirir
    function toggleTrayVisibility() {
        if (isTrayVisible) {
            bottomActionArea.classList.add('visible');
        } else {
            bottomActionArea.classList.remove('visible');
        }
    }

    // Seçilen özellikleri günceller ve tepsiyi tetikler
    const updateSelectedList = () => {
        selectedList.innerHTML = '';
        const activeToggles = document.querySelectorAll('.switch input:checked');
        
        // Tepsinin görünürlüğünü seçime göre ayarla
        isTrayVisible = activeToggles.length > 0;
        toggleTrayVisibility();

        activeToggles.forEach(toggle => {
            const card = toggle.closest('.feature-card');
            const featureName = card.dataset.featureName;
            const featureKey = card.dataset.featureKey;
            
            const listItem = document.createElement('li');
            listItem.textContent = featureName;
            
            const removeBtn = document.createElement('button');
            removeBtn.className = 'remove-feature';
            removeBtn.innerHTML = '&times;';
            removeBtn.dataset.key = featureKey;
            
            listItem.appendChild(removeBtn);
            selectedList.appendChild(listItem);
        });
    };

    // --- Olay Dinleyicileri ---
    
    // Dil Seçimi
    if (langSelector) {
        langCurrentBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            langSelector.classList.toggle('open');
        });
        langOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                const lang = option.getAttribute('data-lang');
                changeLanguage(lang);
                langSelector.classList.remove('open');
            });
        });
        document.addEventListener('click', () => langSelector.classList.remove('open'));
    }

    // Tema Değiştirme
    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', () => {
            const newTheme = body.classList.contains('dark-theme') ? 'light-theme' : 'dark-theme';
            body.className = newTheme;
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }

    // Toggle Buton Olayı (Listeyi Güncelle)
    featureToggles.forEach(toggle => toggle.addEventListener('change', updateSelectedList));

    // Seçilen Listeden Kaldırma Olayı
    selectedList.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-feature')) {
            const featureKeyToRemove = e.target.dataset.key;
            const correspondingToggle = document.querySelector(`.feature-card[data-feature-key="${featureKeyToRemove}"] .switch input`);
            if (correspondingToggle) {
                correspondingToggle.checked = false;
                updateSelectedList();
            }
        }
    });

    // İndir Butonu Olayı (Loglama ve Geri Sayım)
    startButton.addEventListener('click', async () => {
        const lang = localStorage.getItem('userLanguage') || 'tr';
        const langPack = translations[lang] || translations.tr;
        const activeToggles = document.querySelectorAll('.switch input:checked');

        if (activeToggles.length === 0) {
            alert(langPack.alert_no_features);
            return;
        }

        const selectedFeatureKeys = Array.from(activeToggles).map(t => t.closest('.feature-card').dataset.featureKey);
        const isAntennaSelected = selectedFeatureKeys.includes('antenna');

        // YENİ: Antenna seçiliyse geri sayım başlat
        if (isAntennaSelected) {
            // Geri sayım ve link açma işlemini asenkron yap
            (async () => {
                startButton.disabled = true;
                const baseText = langPack.creating_countdown.replace('{s}', ''); // "Oluşturuluyor... "
                
                startButton.textContent = baseText + '3';
                await new Promise(r => setTimeout(r, 1000));
                startButton.textContent = baseText + '2';
                await new Promise(r => setTimeout(r, 1000));
                startButton.textContent = baseText + '1';
                await new Promise(r => setTimeout(r, 1000));
                
                window.open(antennaLink, '_blank');
                startButton.textContent = langPack.start_button;
                startButton.disabled = false;
            })();
        }
        
        // YENİ: Loglama işlemini her zaman (arka planda) yap
        try {
            const response = await fetch('/features/log_usage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ selected_features: selectedFeatureKeys })
            });
            if (!response.ok) { 
                throw new Error('Server response not ok'); 
            }
            // Başarı alert'i kaldırıldı.
        } catch (error) {
            console.error('Config log error:', error);
            alert(langPack.config_fail); // Hata alert'i kaldı.
        }
    });

    // YENİ: Kilitli Kart ve Modal Olay Dinleyicileri
    if (redirectModal) {
        // Kilitli kartlardan herhangi birine tıklandığında modal'ı göster
        lockedCards.forEach(overlay => {
            overlay.addEventListener('click', () => {
                redirectModal.classList.add('visible');
            });
        });

        // Modal'daki "Geri" butonuna tıklanınca modal'ı gizle
        redirectModalBack.addEventListener('click', () => {
            redirectModal.classList.remove('visible');
        });

        // Modal'daki "Devam Et" butonuna tıklanınca abonelik sayfasına yönlendir
        redirectModalContinue.addEventListener('click', () => {
            // index.html'deki url_for('subscriptions_page') referansına dayanarak
            // '/subscriptions' adresine yönlendiriyoruz.
            window.location.href = '/subscriptions'; 
        });

        // Modal'ın dışındaki karanlık alana tıklanınca modal'ı gizle
        redirectModal.addEventListener('click', (e) => {
            if (e.target === redirectModal) {
                redirectModal.classList.remove('visible');
            }
        });
    }

    // --- Uygulamayı Başlat ---
    loadTheme();
    changeLanguage(localStorage.getItem('userLanguage') || 'tr');
    
    // Sayfa yüklendiğinde listenin durumunu kontrol et
    updateSelectedList();
});