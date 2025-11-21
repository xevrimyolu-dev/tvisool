/* © 2025 ToolVision. All Rights Reserved. Unauthorized copying is prohibited. */

document.addEventListener('DOMContentLoaded', () => {
    
    // --- GENEL ELEMANLAR ---
    const body = document.body;
    const cursorGlow = document.getElementById('cursor-glow');
    const authModal = document.getElementById('auth-modal');
    const closeModalButton = document.getElementById('modal-close-button');
    const backdrop = document.getElementById('backdrop');
    const modalContent = document.querySelector('.modal-content');

    // --- MODAL TETİKLEYİCİLERİ ---
    const loginTriggers = document.querySelectorAll('#login-trigger-desktop, #login-trigger-mobile');
    const registerTriggers = document.querySelectorAll('#register-trigger-desktop, #register-trigger-mobile, #main-register-trigger');
    const forgotPasswordLink = document.getElementById('forgot-password-link');
    const backToLoginLink = document.getElementById('back-to-login-link');

    // --- FORM SEKMELERİ VE KONTEYNERLERİ ---
    const loginTab = document.getElementById('login-tab');
    const registerTab = document.getElementById('register-tab');
    const formToggleTabs = document.getElementById('form-toggle-tabs');
    const forgotPasswordTitle = document.getElementById('forgot-password-title');
    const loginFormContainer = document.getElementById('login-form-container');
    const registerFormContainer = document.getElementById('register-form-container');
    const forgotPasswordContainer = document.getElementById('forgot-password-container');
    const flashMessagesContainer = document.getElementById('flash-messages-container');
    
    // --- FORM ELEMANLARI VE DOĞRULAMA ---
    const loginButton = document.getElementById('login-button');
    const registerButton = document.getElementById('register-button');
    const usernameRegisterInput = document.getElementById('username_register');
    const emailRegisterInput = document.getElementById('email_register');
    const passwordRegisterInput = document.getElementById('password_register');
    const loginIdentifierInput = document.getElementById('login_identifier');
    const loginPasswordInput = document.getElementById('password_login');
    const usernameValidationIcon = document.getElementById('username_validation_icon');
    const passwordRulesContainer = document.getElementById('password-rules');
    const emailRulesContainer = document.getElementById('email-rules');

    let debounceTimer;

    // --- CSRF TOKEN FONKSİYONU ---
    function getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }

    // --- FARE TAKİP EFEKTİ ---
    if (cursorGlow) {
        document.addEventListener('mousemove', e => {
            cursorGlow.style.transform = `translate(${e.clientX - 300}px, ${e.clientY - 300}px)`;
        });
    }

    // --- MODAL FORM YÖNETİMİ ---
    function openModal() {
        setFingerprint();
        if(authModal) authModal.classList.add('active');
        if(backdrop) backdrop.classList.add('active');
        adjustModalHeight();
    }

    function closeModal() {
        if(authModal) authModal.classList.remove('active');
        if(backdrop) backdrop.classList.remove('active');
        if (flashMessagesContainer && flashMessagesContainer.parentNode) {
            flashMessagesContainer.parentNode.removeChild(flashMessagesContainer);
        }
        if(modalContent) modalContent.classList.remove('with-flash');
    }

    function showForm(formToShow) {
        if(loginFormContainer) loginFormContainer.classList.add('hidden');
        if(registerFormContainer) registerFormContainer.classList.add('hidden');
        if(forgotPasswordContainer) forgotPasswordContainer.classList.add('hidden');
        if(forgotPasswordTitle) forgotPasswordTitle.classList.add('hidden');
        if(formToggleTabs) formToggleTabs.classList.remove('hidden');

        if (formToShow === 'login') {
            if(loginTab) loginTab.classList.add('active');
            if(registerTab) registerTab.classList.remove('active');
            if(loginFormContainer) loginFormContainer.classList.remove('hidden');
        } else if (formToShow === 'register') {
            if(registerTab) registerTab.classList.add('active');
            if(loginTab) loginTab.classList.remove('active');
            if(registerFormContainer) registerFormContainer.classList.remove('hidden');
        } else if (formToShow === 'forgot_password') {
            if(forgotPasswordContainer) forgotPasswordContainer.classList.remove('hidden');
            if(formToggleTabs) formToggleTabs.classList.add('hidden');
            if(forgotPasswordTitle) forgotPasswordTitle.classList.remove('hidden');
        }
        openModal();
    }
    
    function setFingerprint() {
        if (typeof FingerprintJS === 'undefined') {
            console.error('FingerprintJS kütüphanesi yüklenemedi.');
            return;
        }

        const fpPromise = FingerprintJS.load();

        fpPromise
            .then(fp => fp.get())
            .then(result => {
                const visitorId = result.visitorId;
                
                if (visitorId) {
                    const registerFingerprintInput = document.getElementById('fingerprint_register');
                    const loginFingerprintInput = document.getElementById('fingerprint_login');

                    if (registerFingerprintInput) registerFingerprintInput.value = visitorId;
                    if (loginFingerprintInput) loginFingerprintInput.value = visitorId;
                } else {
                    console.error('Geçerli bir parmak izi (visitorId) alınamadı.');
                }
            })
            .catch(error => console.error('Parmak izi alınırken hata oluştu:', error));
    }

    // --- FLASH MESAJ YÖNETİMİ ---
    function adjustModalHeight() {
        if (flashMessagesContainer && flashMessagesContainer.children.length > 0 && modalContent) {
            modalContent.classList.add('with-flash');
        } else if (modalContent) {
            modalContent.classList.remove('with-flash');
        }
    }

    function setupAutoCloseFlash() {
        document.querySelectorAll('.flash-message').forEach(message => {
            setTimeout(() => {
                if (message.parentNode) {
                    const closeButton = message.querySelector('.flash-close');
                    if (closeButton) closeButton.click();
                }
            }, 7000);
        });
    }

    // --- FLASH MESAJ KAPANMA MANTIĞI (YENİ VE GÜVENLİ YOL) ---
    function initializeFlashMessageClose() {
        const allCloseButtons = document.querySelectorAll('.flash-close');
        
        allCloseButtons.forEach(button => {
            button.addEventListener('click', () => {
                const flashMessage = button.closest('.flash-message');
                if (flashMessage) {
                    // Animasyonlu bir şekilde gizle
                    flashMessage.style.opacity = '0';
                    flashMessage.style.transform = 'translateY(-20px)';
                    
                    // Animasyon bittikten sonra elementi DOM'dan tamamen kaldır
                    setTimeout(() => {
                        if (flashMessage.parentNode) {
                            flashMessage.parentNode.removeChild(flashMessage);
                            // Eğer hiç flash mesaj kalmadıysa, ana konteyneri de kaldırarak boşluğu düzelt
                            if (flashMessagesContainer && flashMessagesContainer.children.length === 0 && flashMessagesContainer.parentNode) {
                                flashMessagesContainer.parentNode.removeChild(flashMessagesContainer);
                                if(modalContent) modalContent.classList.remove('with-flash');
                            }
                        }
                    }, 300);
                }
            });
        });
    }

    // --- MOBİL MENÜ MANTIĞI ---
    const mobileNavToggle = document.getElementById('mobile-nav-toggle');
    const mobileNav = document.getElementById('mobile-nav');
    
    const closeMobileMenu = () => {
        if(mobileNavToggle) mobileNavToggle.classList.remove('active');
        if(mobileNav) mobileNav.classList.remove('nav-open');
        if (authModal && !authModal.classList.contains('active')) {
            if(backdrop) backdrop.classList.remove('active');
        }
        if(body) body.classList.remove('menu-open');
    };

    if (mobileNavToggle) {
        mobileNavToggle.addEventListener('click', () => {
            if(body.classList.contains('menu-open')) {
                closeMobileMenu();
            } else {
                mobileNavToggle.classList.add('active');
                mobileNav.classList.add('nav-open');
                backdrop.classList.add('active');
                body.classList.add('menu-open');
            }
        });

        backdrop.addEventListener('click', () => {
            if (body.classList.contains('menu-open')) closeMobileMenu();
            if (authModal && authModal.classList.contains('active')) closeModal();
        });

        if (mobileNav) {
            mobileNav.querySelectorAll('a').forEach(link => {
                link.addEventListener('click', () => setTimeout(closeMobileMenu, 150));
            });
        }
    }

    // --- ŞİFRE GÖSTER/GİZLE ---
    function setupPasswordToggle(passwordInputId, toggleButtonId) {
        const passwordInput = document.getElementById(passwordInputId);
        const toggleButton = document.getElementById(toggleButtonId);
        if (passwordInput && toggleButton) {
            toggleButton.addEventListener('click', function () {
                const isPassword = passwordInput.type === 'password';
                passwordInput.type = isPassword ? 'text' : 'password';
                const icon = this.querySelector('i');
                if(icon) {
                    icon.classList.toggle('fa-eye-slash', !isPassword);
                    icon.classList.toggle('fa-eye', isPassword);
                }
            });
        }
    }
    
    setupPasswordToggle('password_login', 'togglePassword_login');
    setupPasswordToggle('password_register', 'togglePassword_register');
    
    // --- ANLIK FORM DOĞRULAMA (VALIDATION) VE BUTON KONTROLÜ ---
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    const allowedEmailDomains = ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "mail.com", "yandex.com", "protonmail.com"];

    function validateAndToggleButton(formType) {
        if (formType === 'register' && registerButton) {
            const username = usernameRegisterInput.value;
            const email = emailRegisterInput.value;
            const password = passwordRegisterInput.value;
            const emailParts = email.split('@');
            const emailDomain = emailParts.length > 1 ? emailParts[1] : '';
            const isUsernameValid = /^[a-zA-Z0-9_]{3,15}$/.test(username);
            const isEmailValid = emailRegex.test(email) && email.length <= 25 && allowedEmailDomains.includes(emailDomain);
            const isPasswordValid = password.length >= 8 && password.length <= 20 && /[A-Z]/.test(password) && /[!@#$%^&*(),.?":{}|<>]/.test(password);
            registerButton.disabled = !(isUsernameValid && isEmailValid && isPasswordValid);

        } else if (formType === 'login' && loginButton) {
            const isIdentifierValid = loginIdentifierInput.value.length > 0;
            const isPasswordValid = loginPasswordInput.value.length >= 8;
            loginButton.disabled = !(isIdentifierValid && isPasswordValid);
        }
    }
    
    function updateRuleValidation(element, isValid) {
        if (!element) return;
        const icon = element.querySelector('i');
        element.classList.toggle('valid', isValid);
        if (icon) {
            icon.classList.toggle('fa-times', !isValid);
            icon.classList.toggle('fa-check', isValid);
        }
    }

    if (registerFormContainer) {
        usernameRegisterInput.addEventListener('keyup', () => {
            clearTimeout(debounceTimer);
            validateAndToggleButton('register');
            const username = usernameRegisterInput.value;
            if (username.length < 3) {
                usernameValidationIcon.className = 'validation-icon invalid visible';
                return;
            }
            usernameValidationIcon.className = 'validation-icon loading visible';
            debounceTimer = setTimeout(() => {
                fetch('/check_username', {
                    method: 'POST', 
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
                    body: JSON.stringify({ username: username })
                }).then(res => res.json()).then(data => {
                    usernameValidationIcon.className = data.available ? 'validation-icon valid visible' : 'validation-icon invalid visible';
                }).catch(() => { usernameValidationIcon.className = 'validation-icon invalid visible'; });
            }, 300);
        });

        emailRegisterInput.addEventListener('focus', () => emailRulesContainer.classList.remove('hidden'));
        emailRegisterInput.addEventListener('keyup', () => {
            const email = emailRegisterInput.value.trim();
            const emailParts = email.split('@');
            const domain = emailParts.length > 1 ? emailParts[1] : '';
            const isFormatValid = emailRegex.test(email) && email.length <= 25;
            const isProviderValid = isFormatValid && allowedEmailDomains.includes(domain);
            updateRuleValidation(document.getElementById('rule-email-format'), isFormatValid);
            updateRuleValidation(document.getElementById('rule-email-provider'), isProviderValid);
            validateAndToggleButton('register');
        });

        passwordRegisterInput.addEventListener('focus', () => passwordRulesContainer.classList.remove('hidden'));
        passwordRegisterInput.addEventListener('keyup', () => {
            const password = passwordRegisterInput.value;
            updateRuleValidation(document.getElementById('rule-length'), password.length >= 8);
            updateRuleValidation(document.getElementById('rule-uppercase'), /[A-Z]/.test(password));
            updateRuleValidation(document.getElementById('rule-special'), /[!@#$%^&*(),.?":{}|<>]/.test(password));
            validateAndToggleButton('register');
        });
    }

    if (loginFormContainer) {
        loginIdentifierInput.addEventListener('keyup', () => validateAndToggleButton('login'));
        loginPasswordInput.addEventListener('keyup', () => validateAndToggleButton('login'));
    }

    // --- OLAY DİNLEYİCİLERİ (EVENT LISTENERS) ---
    loginTriggers.forEach(btn => {
        btn.addEventListener('click', e => {
            e.preventDefault();
            showForm('login');
        });
    });

    registerTriggers.forEach(btn => {
        btn.addEventListener('click', e => {
            e.preventDefault();
            showForm('register');
        });
    });

    if (loginTab) {
        loginTab.addEventListener('click', e => {
            e.preventDefault();
            showForm('login');
        });
    }

    if (registerTab) {
        registerTab.addEventListener('click', e => {
            e.preventDefault();
            showForm('register');
        });
    }

    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener('click', e => {
            e.preventDefault();
            showForm('forgot_password');
        });
    }

    if (backToLoginLink) {
        backToLoginLink.addEventListener('click', e => {
            e.preventDefault();
            showForm('login');
        });
    }

    if (closeModalButton) {
        closeModalButton.addEventListener('click', closeModal);
    }

    if (authModal) {
        authModal.addEventListener('click', e => {
            if (e.target === authModal) closeModal();
        });
    }
    
    // --- SAYFA YÜKLENDİĞİNDE MODAL KONTROLÜ ---
    const urlParams = new URLSearchParams(window.location.search);
    const fromParam = urlParams.get('from');

    if (fromParam) {
        showForm(fromParam);
        setupAutoCloseFlash();
    } else if (flashMessagesContainer && flashMessagesContainer.children.length > 0) {
        // Flash mesaj varsa login formunu göster
        showForm('login'); 
        setupAutoCloseFlash();
    }

    // --- FLASH MESAJ KAPATMA YÖNETİMİNİ BAŞLAT ---
    initializeFlashMessageClose();

    // --- GOOGLE GİRİŞ İÇİN PARMAK İZİ KAYDETME ---
    const googleLoginButton = document.getElementById("google-login-button");
    if (googleLoginButton) {
        googleLoginButton.addEventListener("click", async function(event) {
            // Linkin varsayılan davranışını (hemen yönlenme) engelle
            event.preventDefault(); 
            
            const originalHref = this.href; // Orijinal Google login URL'si
            let visitorId = null;

            try {
                // Parmak izini al
                if (typeof FingerprintJS !== 'undefined') {
                    const fp = await FingerprintJS.load();
                    const result = await fp.get();
                    visitorId = result.visitorId;
                }
            } catch (error) {
                console.error("Parmak izi alınırken hata:", error);
                // Hata olsa bile devam et (log kaydı tut)
            }

            if (visitorId) {
                try {
                    // Parmak izini sunucuya (session'a) kaydetmek için endpoint'e istek gönder
                    await fetch('/store_fingerprint', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCSRFToken() // Mevcut CSRF token fonksiyonunuz
                        },
                        body: JSON.stringify({ fingerprint: visitorId })
                    });
                } catch (error) {
                    console.error("Parmak izi kaydedilemedi:", error);
                }
            }

            // Parmak izi kaydedildikten (veya hata alındıktan) sonra
            // kullanıcıyı asıl Google login URL'sine yönlendir
            window.location.href = originalHref;
        });
    }

}); // DOMContentLoaded'in kapanış etiketi