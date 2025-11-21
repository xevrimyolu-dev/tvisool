// static/js/reset_password.js

document.addEventListener('DOMContentLoaded', () => {

    // --- ŞİFRE GÖSTER/GİZLE İŞLEVSELLİĞİ ---
    function setupPasswordToggle(passwordInputId, toggleButtonId) {
        const passwordInput = document.getElementById(passwordInputId);
        const toggleButton = document.getElementById(toggleButtonId);

        if (passwordInput && toggleButton) {
            toggleButton.addEventListener('click', function () {
                const isPassword = passwordInput.type === 'password';
                passwordInput.type = isPassword ? 'text' : 'password';

                const icon = this.querySelector('i');
                if (icon) {
                    icon.classList.toggle('fa-eye-slash', !isPassword);
                    icon.classList.toggle('fa-eye', isPassword);
                }
            });
        }
    }

    // Oluşturduğumuz HTML'deki ID'lerle fonksiyonu çağırıyoruz
    setupPasswordToggle('password_reset', 'togglePassword_reset');

    // --- ANLIK ŞİFRE KURALLARI KONTROLÜ ---
    const passwordResetInput = document.getElementById('password_reset');
    const passwordRulesContainer = document.getElementById('password-rules');
    
    if (passwordResetInput && passwordRulesContainer) {
        const rules = {
            length: { el: document.getElementById('rule-length'), validator: (val) => val.length >= 8 },
            uppercase: { el: document.getElementById('rule-uppercase'), validator: (val) => /[A-Z]/.test(val) },
            special: { el: document.getElementById('rule-special'), validator: (val) => /[!@#$%^&*(),.?":{}|<>]/.test(val) }
        };
        
        // Input'a tıklandığında kuralları her zaman göster
        passwordResetInput.addEventListener('focus', () => {
            passwordRulesContainer.classList.remove('hidden');
        });

        // Kullanıcı şifre yazdıkça kuralları kontrol et
        passwordResetInput.addEventListener('keyup', () => {
            const password = passwordResetInput.value;

            for (const ruleName in rules) {
                const rule = rules[ruleName];
                const icon = rule.el.querySelector('i');
                const isValid = rule.validator(password);
                
                rule.el.classList.toggle('valid', isValid);
                icon.classList.toggle('fa-times', !isValid);
                icon.classList.toggle('fa-check', isValid);
            }
        });
    }

});