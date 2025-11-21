let ytPlayer;
let currentVideoKey = null;
let currentVideoType = 'local';
let logInterval = null;
let isPipActive = false;

function onYouTubeIframeAPIReady() {
}

document.addEventListener('DOMContentLoaded', () => {

    const translations = {
        tr: {
            coding_videos_title: "KODLAMA VİDEOLARI",
            video_1_title: "Video 1: Kodlama Hakkında Bilmeniz Gerekenler",
            video_2_title: "Video 2: Aimbot Özelliği Entegrasyonu",
            video_3_title: "Video 3: Paketlenmiş Oyuncu Verileri",
            purchase_to_unlock: "Kilidi Açmak İçin Satın Al",
            tools_used: "Kullanılan Araçlar",
            video_1_tool_1: ".uasset & .uexp Görüntüleyici",
            video_1_tool_2: "Örnek Proje Dosyaları",
            video_2_tool_1: "Aimbot Entegrasyon Kiti",
            no_tools_used: "Bu videoda hiçbir araç kullanılmamıştır",
            continue_watching_prompt: "En son kaldığınız yerden devam etmek ister misiniz?",
            restart_video: "Baştan Başlat",
            continue_watching: "Devam Et",
            lang_native: "Türkçe",
            redirect_to_subs_prompt: "Abonelik sayfasına yönlendirileceksiniz",
            modal_back: "Geri",
            modal_continue: "Devam Et"
        },
        en: {
            coding_videos_title: "CODING VIDEOS",
            video_1_title: "Video 1: What You Need to Know About Coding",
            video_2_title: "Video 2: Aimbot Feature Integration",
            video_3_title: "Video 3: Packed Player Data",
            purchase_to_unlock: "Purchase to Unlock",
            tools_used: "Tools Used",
            video_1_tool_1: ".uasset & .uexp Viewer",
            video_1_tool_2: "Sample Project Files",
            video_2_tool_1: "Aimbot Integration Kit",
            no_tools_used: "No tools were used in this video",
            continue_watching_prompt: "Do you want to continue where you left off?",
            restart_video: "Restart",
            continue_watching: "Continue",
            lang_native: "English",
            redirect_to_subs_prompt: "You will be redirected to the subscriptions page",
            modal_back: "Back",
            modal_continue: "Continue"
        },
        fr: {
            coding_videos_title: "VIDÉOS DE CODAGE",
            video_1_title: "Vidéo 1: Ce que vous devez savoir sur le codage",
            video_2_title: "Vidéo 2: Intégration de la fonction Aimbot",
            video_3_title: "Vidéo 3: Données de joueur emballées",
            purchase_to_unlock: "Acheter pour déverrouiller",
            tools_used: "Outils utilisés",
            video_1_tool_1: "Visualiseur .uasset & .uexp",
            video_1_tool_2: "Fichiers de projet d'exemple",
            video_2_tool_1: "Kit d'intégration Aimbot",
            no_tools_used: "Aucun outil n'a été utilisé dans cette vidéo",
            continue_watching_prompt: "Voulez-vous continuer là où vous vous êtes arrêté ?",
            restart_video: "Recommencer",
            continue_watching: "Continuer",
            lang_native: "Français",
            redirect_to_subs_prompt: "Vous serez redirigé vers la page des abonnements",
            modal_back: "Retour",
            modal_continue: "Continuer"
        },
        es: {
            coding_videos_title: "VÍDEOS DE CODIFICACIÓN",
            video_1_title: "Video 1: Lo que necesita saber sobre la codificación", 
            video_2_title: "Video 2: Integración de la función Aimbot",
            video_3_title: "Video 3: Datos del jugador empaquetados",
            purchase_to_unlock: "Comprar para desbloquear",
            tools_used: "Herramientas utilizadas",
            video_1_tool_1: "Visor de .uasset y .uexp",
            video_1_tool_2: "Archivos de proyecto de muestra",
            video_2_tool_1: "Kit de integración de Aimbot",
            no_tools_used: "No se utilizaron herramientas en este video",
            continue_watching_prompt: "¿Quieres continuar donde lo dejaste?",
            restart_video: "Reiniciar",
            continue_watching: "Continuar",
            lang_native: "Español",
            redirect_to_subs_prompt: "Será redirigido a la página de suscripciones",
            modal_back: "Atrás",
            modal_continue: "Continuar"
        },
        zh: {
            coding_videos_title: "编程视频",
            video_1_title: "视频1：关于编码您需要了解的内容",
            video_2_title: "视频2：自瞄功能集成",
            video_3_title: "视频3：打包的玩家数据",
            purchase_to_unlock: "购买以解锁",
            tools_used: "使用的工具",
            video_1_tool_1: ".uasset 和 .uexp 查看器",
            video_1_tool_2: "示例项目文件",
            video_2_tool_1: "自瞄集成套件",
            no_tools_used: "此视频未使用任何工具",
            continue_watching_prompt: "您想从上次离开的地方继续吗？",
            restart_video: "重新开始",
            continue_watching: "继续",
            lang_native: "中文",
            redirect_to_subs_prompt: "您将被重定向到订阅页面",
            modal_back: "返回",
            modal_continue: "继续"
        },
        ja: {
            coding_videos_title: "コーディングビデオ",
            video_1_title: "ビデオ1：コーディングについて知っておくべきこと",
            video_2_title: "ビデオ2：エイムボット機能の統合",
            video_3_title: "ビデオ3：パックされたプレイヤーデータ",
            purchase_to_unlock: "購入してロック解除",
            tools_used: "使用ツール",
            video_1_tool_1: ".uasset & .uexpビューア",
            video_1_tool_2: "サンプルプロジェクトファイル",
            video_2_tool_1: "エイムボット統合キット",
            no_tools_used: "このビデオではツールは使用されていません",
            continue_watching_prompt: "中断したところから続けますか？",
            restart_video: "最初から再生",
            continue_watching: "続ける",
            lang_native: "日本語",
            redirect_to_subs_prompt: "サブスクリプションページにリダイレクトされます",
            modal_back: "戻る",
            modal_continue: "続行"
        },
        ko: {
            coding_videos_title: "코딩 비디오",
            video_1_title: "비디오 1: 코딩에 대해 알아야 할 사항",
            video_2_title: "비디오 2: 에임봇 기능 통합",
            video_3_title: "비디오 3: 패킹된 플레이어 데이터",
            purchase_to_unlock: "구매하여 잠금 해제",
            tools_used: "사용된 도구",
            video_1_tool_1: ".uasset & .uexp 뷰어",
            video_1_tool_2: "샘플 프로젝트 파일",
            video_2_tool_1: "에임봇 통합 키트",
            no_tools_used: "이 비디오에는 도구가 사용되지 않았습니다",
            continue_watching_prompt: "중단한 부분부터 계속하시겠습니까?",
            restart_video: "처음부터 시작",
            continue_watching: "계속하기",
            lang_native: "한국어",
            redirect_to_subs_prompt: "구독 페이지로 리디렉션됩니다",
            modal_back: "뒤로",
            modal_continue: "계속"
        },
        hi: {
            coding_videos_title: "कोडिंग वीडियो",
            video_1_title: "वीडियो 1: कोडिंग के बारे में आपको क्या जानना चाहिए",
            video_2_title: "वीडियो 2: एमबॉट फ़ीचर इंटीग्रेशन",
            video_3_title: "वीडियो 7: पैक्ड प्लेयर डेटा",
            purchase_to_unlock: "अनलॉक करने के लिए खरीदें",
            tools_used: "उपयोग किए गए उपकरण",
            video_1_tool_1: ".uasset और .uexp व्यूअर",
            video_1_tool_2: "नमूना प्रोजेक्ट फ़ाइलें",
            video_2_tool_1: "एमबॉट इंटीग्रेशन किट",
            no_tools_used: "इस वीडियो में किसी टूल का इस्तेमाल नहीं किया गया",
            continue_watching_prompt: "क्या आप वहीं से जारी रखना चाहते हैं जहाँ आपने छोड़ा था?",
            restart_video: "पुनः आरंभ करें",
            continue_watching: "जारी रखें",
            lang_native: "हिन्दी",
            redirect_to_subs_prompt: "आपको सदस्यता पृष्ठ पर पुनः निर्देशित किया जाएगा",
            modal_back: "वापस",
            modal_continue: "जारी रखें"
        }
    };

    function applyTranslations(lang) {
        const langPack = translations[lang] || translations.tr;
        document.querySelectorAll('[data-lang-key]').forEach(el => {
            const key = el.getAttribute('data-lang-key');
            if (langPack[key]) {
                el.textContent = langPack[key];
            }
        });
        const langCurrentBtn = document.querySelector('.lang-current');
        if (langCurrentBtn) {
            langCurrentBtn.querySelector('img').src = `/static/images/${lang}.png`;
        }
    }

    const videoCards = document.querySelectorAll('.video-card');
    const modal = document.getElementById('videoPlayerModal');
    const videoPlayer = document.getElementById('mainVideoPlayer');
    const youtubePlayerContainer = document.getElementById('youtubePlayerContainer');
    const closeModalBtn = document.querySelector('.video-modal-close');
    const continuePrompt = document.getElementById('continuePrompt');
    const restartVideoBtn = document.getElementById('restartVideoBtn');
    const continueVideoBtn = document.getElementById('continueVideoBtn');
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    const langSelector = document.querySelector('.language-selector');
    const langOptions = document.querySelectorAll('.lang-option');
    const body = document.body;
    const themeToggleButton = document.getElementById('themeToggleButton');

    const redirectModal = document.getElementById('subscriptionRedirectModal');
    const redirectModalContinue = document.getElementById('modalRedirectContinue');
    const redirectModalBack = document.getElementById('modalRedirectBack');
    const lockedCards = document.querySelectorAll('.video-card.locked .lock-overlay');
    
    function changeLanguage(lang) {
        if (!translations[lang]) lang = 'tr';
        localStorage.setItem('userLanguage', lang);
        applyTranslations(lang);
    }
    const userLang = localStorage.getItem('userLanguage') || 'tr';
    changeLanguage(userLang);

    function loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark-theme';
        body.className = '';
        body.classList.add(savedTheme);
        updateThemeIcon(savedTheme);
    }
    function updateThemeIcon(theme) {
        if (themeToggleButton) {
            themeToggleButton.querySelector('i').className = theme === 'dark-theme' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }
    loadTheme();

    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', () => {
            const isDark = body.classList.contains('dark-theme');
            const newTheme = isDark ? 'light-theme' : 'dark-theme';
            body.classList.remove('dark-theme', 'light-theme');
            body.classList.add(newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }

    if (langSelector) {
        langSelector.addEventListener('click', (e) => {
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

    document.querySelectorAll('.tools-toggle-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            
            button.classList.toggle('open');
            const content = button.nextElementSibling;
            if (content.style.maxHeight) {
                content.style.maxHeight = null;
            } else {
                content.style.maxHeight = content.scrollHeight + "px";
            }
        });
    });

    videoCards.forEach(card => {
        card.addEventListener('click', (e) => {
            if (card.classList.contains('locked') || e.target.closest('.tools-toggle-btn') || e.target.closest('a')) {
                return;
            }
            
            currentVideoKey = card.dataset.videoKey;
            const videoFile = card.dataset.videoFile;
            const youtubeId = card.dataset.youtubeId;

            if (videoFile === 'youtube' && youtubeId) {
                currentVideoType = 'youtube';
                videoPlayer.style.display = 'none';
                youtubePlayerContainer.style.display = 'block';
                
                if (!ytPlayer) {
                    ytPlayer = new YT.Player('youtubePlayerContainer', {
                        height: '100%',
                        width: '100%',
                        videoId: youtubeId,
                        playerVars: {
                            'playsinline': 1,
                            'controls': 1,
                            'rel': 0,
                            'modestbranding': 1
                        },
                        events: {
                            'onReady': onPlayerReady,
                            'onStateChange': onPlayerStateChange
                        }
                    });
                } else {
                    ytPlayer.loadVideoById(youtubeId);
                    openModal();
                }
            } else {
                currentVideoType = 'local';
                videoPlayer.style.display = 'block';
                youtubePlayerContainer.style.display = 'none';
                videoPlayer.src = videoFile;
                openModal();
            }
        });
    });
    
    function onPlayerReady(event) {
        openModal();
    }
    
    function onPlayerStateChange(event) {
        if (event.data == YT.PlayerState.PLAYING) {
            startLoggingProgress();
        } else if (event.data == YT.PlayerState.PAUSED || event.data == YT.PlayerState.ENDED) {
            stopLoggingProgress();
            saveProgress();
        }
    }

    closeModalBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    videoPlayer.addEventListener('enterpictureinpicture', () => { isPipActive = true; });
    videoPlayer.addEventListener('leavepictureinpicture', () => { isPipActive = false; });
    
    function openModal() {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        const savedTime = localStorage.getItem(`video_progress_${currentVideoKey}`);
        
        if (savedTime && parseFloat(savedTime) > 5) {
            continuePrompt.style.display = 'block';
            
            continueVideoBtn.onclick = () => {
                if (currentVideoType === 'youtube' && ytPlayer) {
                    ytPlayer.seekTo(parseFloat(savedTime), true);
                } else {
                    videoPlayer.currentTime = parseFloat(savedTime);
                }
                startPlayback();
            };
            
            restartVideoBtn.onclick = () => {
                if (currentVideoType === 'youtube' && ytPlayer) {
                    ytPlayer.seekTo(0, true);
                } else {
                    videoPlayer.currentTime = 0;
                }
                startPlayback();
            };
        } else {
            startPlayback();
        }
    }

    function startPlayback() {
        continuePrompt.style.display = 'none';
        if (currentVideoType === 'youtube' && ytPlayer) {
            ytPlayer.playVideo();
        } else {
            videoPlayer.play();
            startLoggingProgress(); 
        }
    }

    function closeModal() {
        if (currentVideoType === 'local' && isPipActive) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
            return; 
        }

        stopLoggingProgress();
        saveProgress();
        
        if (currentVideoType === 'youtube' && ytPlayer) {
            ytPlayer.pauseVideo();
        } else {
            videoPlayer.pause();
            videoPlayer.src = "";
        }

        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        currentVideoKey = null;
    }

    function saveProgress() {
        if (currentVideoKey) {
            let time = 0;
            if (currentVideoType === 'youtube' && ytPlayer && typeof ytPlayer.getCurrentTime === 'function') {
                time = ytPlayer.getCurrentTime();
            } else {
                time = videoPlayer.currentTime;
            }
            if (time > 0) {
                localStorage.setItem(`video_progress_${currentVideoKey}`, time);
            }
        }
    }

    function startLoggingProgress() {
        if (logInterval) clearInterval(logInterval);
        logInterval = setInterval(() => {
            let time = 0;
            let isPaused = true;
            
            if (currentVideoType === 'youtube' && ytPlayer && typeof ytPlayer.getCurrentTime === 'function') {
                time = ytPlayer.getCurrentTime();
                isPaused = ytPlayer.getPlayerState() !== YT.PlayerState.PLAYING;
            } else {
                time = videoPlayer.currentTime;
                isPaused = videoPlayer.paused;
            }

            if (!isPaused && currentVideoKey) {
                sendProgressToServer(time);
            }
        }, 15000);
    }

    function stopLoggingProgress() {
        if (logInterval) {
            clearInterval(logInterval);
            logInterval = null;
            
            let time = 0;
            if (currentVideoType === 'youtube' && ytPlayer && typeof ytPlayer.getCurrentTime === 'function') {
                time = ytPlayer.getCurrentTime();
            } else {
                time = videoPlayer.currentTime;
            }

            if (currentVideoKey && time > 0) {
                 sendProgressToServer(time);
            }
        }
    }

    async function sendProgressToServer(time) {
        try {
            await fetch('/videos/log_progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    video_key: currentVideoKey,
                    currentTime: time
                })
            });
        } catch (error) {
            console.error("İlerleme kaydedilirken hata:", error);
        }
    }
    
    if (redirectModal) {
        lockedCards.forEach(overlay => {
            overlay.addEventListener('click', () => {
                redirectModal.classList.add('visible');
            });
        });

        redirectModalBack.addEventListener('click', () => {
            redirectModal.classList.remove('visible');
        });

        redirectModalContinue.addEventListener('click', () => {
            window.location.href = '/subscriptions'; 
        });

        redirectModal.addEventListener('click', (e) => {
            if (e.target === redirectModal) {
                redirectModal.classList.remove('visible');
            }
        });
    }
});