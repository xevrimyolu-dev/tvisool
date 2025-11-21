// payment.js

// Yeni dil çevirileri ve getLang fonksiyonu (script.js'e bağımlı)
const paymentTranslations = {
    'tr': {
        'payment_options_title': 'Ödeme Yöntemi Seçimi',
        'back_to_subscriptions': 'Aboneliklere Geri Dön',
        'back_to_select': 'Geri',
        'payment_method_qr': 'QR Kod ile Ödeme',
        'payment_method_transfer': 'Transfer ile Ödeme',
        'qr_select_title': 'QR Kod Seçimi',
        'transfer_select_title': 'Transfer Detayları',
        'summary_header': 'Ödenecek Plan Özeti',
        'role_label': 'Rol:',
        'duration_label': 'Süre:',
        'price_label': 'Ödenecek Tutar:',
        'transfer_instructions': 'Lütfen aşağıdaki bilgileri kullanarak ödeme yapın. Hesap bilgilerine dokunarak kopyalayabilirsiniz.',
        'payment_completed_btn': 'Ödemeyi Yaptım',
        'payment_crypto': 'Kripto',
        'payment_famapp': 'FamApp',
        'payment_paytm': 'PayTM',
        'payment_paypal': 'PayPal',
        'copied_to_clipboard': 'Panoya kopyalandı!',
        'payment_crypto_info': 'YATIRIM: USDT, Ağ: Tron (TRC20)',
        'intent_recorded_redirecting': 'Niyet kaydedildi. Yönlendiriliyor...',
        'payment_notification_sending': 'Ödeme bildirimi gönderiliyor...',
        'payment_notification_success': 'Ödeme bildirimi başarılı. Yönetici onayı bekleniyor.',
        'payment_notification_error': 'Bildirim gönderilirken hata oluştu.',
        'server_unreachable_error': 'Ağ hatası veya sunucuya ulaşılamadı.',
        'proof_of_payment_title': 'Ödeme Kanıtı',
        'phone_placeholder': 'Telefon Numaranız',
        'email_label': 'E-posta Adresi',
        'email_placeholder': 'E-posta Adresiniz',
		'username_label': 'Kullanıcı Adınız',
        'receipt_label': 'Ödeme Dekontu (Max 10MB: png, jpg, webp)',
        'receipt_upload_btn': 'Dekont Yükle',
        'submit_proof_btn': 'Kanıtı Gönder',
        'verifying_receipt': 'Doğrulanıyor...',
        'verification_failed_title': 'Doğrulama Başarısız',
        'verification_failed_message': 'Lütfen dekontu kontrol edin veya yeni bir dekont yükleyin.',
        'verification_success_title': 'Doğrulama Başarılı',
        'verification_success_message': 'Dekontunuz doğrulandı. Yönetici onayı bekleniyor.',
        'back_to_proof_form': 'Geri',
        'error_uploading_receipt': 'Dekont yüklenirken bir hata oluştu.',
        'error_invalid_file_type': 'Geçersiz dosya türü. Sadece png, jpg, jpeg veya webp yükleyebilirsiniz.',
        'error_file_too_large': 'Dosya çok büyük. Maksimum 10MB.',
        'error_form_incomplete': 'Lütfen tüm alanları doldurun ve bir dekont yükleyin.',
        'error_validation_failed': 'Form doğrulama hatası. Lütfen alanları kontrol edin.'
    },
    'en': {
        'payment_options_title': 'Select Payment Method',
        'back_to_subscriptions': 'Back to Subscriptions',
        'back_to_select': 'Back',
        'payment_method_qr': 'Pay with QR Code',
        'payment_method_transfer': 'Transfer Payment',
        'qr_select_title': 'QR Code Selection',
        'transfer_select_title': 'Transfer Details',
        'summary_header': 'Payment Plan Summary',
        'role_label': 'Role:',
        'duration_label': 'Duration:',
        'price_label': 'Amount Due:',
        'transfer_instructions': 'Please make the payment using the information below. You can copy the account details by tapping them.',
        'payment_completed_btn': 'I Have Paid',
        'payment_crypto': 'Crypto',
		'username_label': 'Your Username',
        'payment_famapp': 'FamApp',
        'payment_paytm': 'PayTM',
        'payment_paypal': 'PayPal',
        'copied_to_clipboard': 'Copied to clipboard!',
        'payment_crypto_info': 'DEPOSIT: USDT, Network: Tron (TRC20)',
        'intent_recorded_redirecting': 'Intent recorded. Redirecting...',
        'payment_notification_sending': 'Sending payment notification...',
        'payment_notification_success': 'Payment notification successful. Waiting for admin approval.',
        'payment_notification_error': 'An error occurred while sending the notification.',
        'server_unreachable_error': 'Network error or server unreachable.',
        'proof_of_payment_title': 'Payment Proof',
        'phone_placeholder': 'Your Phone Number',
        'email_label': 'Email Address',
        'email_placeholder': 'Your Email Address',
        'receipt_label': 'Payment Receipt (Max 10MB: png, jpg, webp)',
        'receipt_upload_btn': 'Upload Receipt',
        'submit_proof_btn': 'Submit Proof',
        'verifying_receipt': 'Verifying...',
        'verification_failed_title': 'Verification Failed',
        'verification_failed_message': 'Please check the receipt or upload a new receipt.',
        'verification_success_title': 'Verification Successful',
        'verification_success_message': 'Your receipt has been verified. Waiting for admin approval.',
        'back_to_proof_form': 'Back',
        'error_uploading_receipt': 'An error occurred while uploading the receipt.',
        'error_invalid_file_type': 'Invalid file type. You can only upload png, jpg, jpeg or webp.',
        'error_file_too_large': 'File too large. Maximum 10MB.',
        'error_form_incomplete': 'Please fill all fields and upload a receipt.',
        'error_validation_failed': 'Form validation error. Please check the fields.'
    },
    'fr': {
        'payment_options_title': 'Sélectionner la Méthode de Paiement',
        'back_to_subscriptions': 'Retour aux Abonnements',
        'back_to_select': 'Retour',
        'payment_method_qr': 'Payer par Code QR',
        'payment_method_transfer': 'Paiement par Virement',
        'qr_select_title': 'Sélection du Code QR',
        'transfer_select_title': 'Détails du Virement',
		'username_label': 'Votre Nom d\'utilisateur',
        'summary_header': 'Résumé du Plan à Payer',
        'role_label': 'Rôle :',
        'duration_label': 'Durée :',
        'price_label': 'Montant dû :',
        'transfer_instructions': 'Veuillez effectuer le paiement en utilisant les informations ci-dessous. Vous pouvez copier les détails en tapotant dessus.',
        'payment_completed_btn': 'J\'ai Payé',
        'payment_crypto': 'Crypto',
        'payment_famapp': 'FamApp',
        'payment_paytm': 'PayTM',
        'payment_paypal': 'PayPal',
        'copied_to_clipboard': 'Copié dans le presse-papiers !',
        'payment_crypto_info': 'DÉPÔT : USDT, Réseau : Tron (TRC20)',
        'intent_recorded_redirecting': 'Intention enregistrée. Redirection en cours...',
        'payment_notification_sending': 'Envoi de la notification de paiement...',
        'payment_notification_success': 'Notification envoyée avec succès. En attente de l\'approbation de l\'administrateur.',
        'payment_notification_error': 'Une erreur est survenue lors de l\'envoi de la notification.',
        'server_unreachable_error': 'Erreur réseau ou serveur inaccessible.',
        'proof_of_payment_title': 'Preuve de Paiement',
        'phone_placeholder': 'Votre Numéro de Téléphone',
        'email_label': 'Adresse Email',
        'email_placeholder': 'Votre Adresse Email',
        'receipt_label': 'Reçu de Paiement (Max 10MB: png, jpg, webp)',
        'receipt_upload_btn': 'Télécharger le Reçu',
        'submit_proof_btn': 'Soumettre la Preuve',
        'verifying_receipt': 'Vérification en cours...',
        'verification_failed_title': 'Échec de la Vérification',
        'verification_failed_message': 'Veuillez vérifier le reçu ou télécharger un nouveau reçu.',
        'verification_success_title': 'Vérification Réussie',
        'verification_success_message': 'Votre reçu a été vérifié. En attente de l\'approbation de l\'administrateur.',
        'back_to_proof_form': 'Retour',
        'error_uploading_receipt': 'Une erreur est survenue lors du téléchargement du reçu.',
        'error_invalid_file_type': 'Type de fichier invalide. Vous ne pouvez télécharger que png, jpg, jpeg ou webp.',
        'error_file_too_large': 'Fichier trop volumineux. Maximum 10MB.',
        'error_form_incomplete': 'Veuillez remplir tous les champs et télécharger un reçu.',
        'error_validation_failed': 'Erreur de validation du formulaire. Veuillez vérifier les champs.'
    },
    'es': {
        'payment_options_title': 'Seleccionar Método de Pago',
        'back_to_subscriptions': 'Volver a Suscripciones',
        'back_to_select': 'Atrás',
        'payment_method_qr': 'Pagar con Código QR',
        'payment_method_transfer': 'Pago por Transferencia',
        'qr_select_title': 'Selección de Código QR',
        'transfer_select_title': 'Detalles de la Transferencia',
        'summary_header': 'Resumen del Plan a Pagar',
        'role_label': 'Rol:',
        'duration_label': 'Duración:',
        'price_label': 'Cantidad a Pagar:',
        'transfer_instructions': 'Por favor, realice el pago utilizando la información a continuación. Puede copiar los detalles de la cuenta tocándolos.',
        'payment_completed_btn': 'He Pagado',
        'payment_crypto': 'Cripto',
        'payment_famapp': 'FamApp',
        'payment_paytm': 'PayTM',
		'username_label': 'Su Nombre de Usuario',
        'payment_paypal': 'PayPal',
        'copied_to_clipboard': '¡Copiado al portapapeles!',
        'payment_crypto_info': 'DEPÓSITO: USDT, Red: Tron (TRC20)',
        'intent_recorded_redirecting': 'Intento registrado. Redirigiendo...',
        'payment_notification_sending': 'Enviando notificación de pago...',
        'payment_notification_success': 'Notificación de pago exitosa. Esperando aprobación del administrador.',
        'payment_notification_error': 'Ocurrió un error al enviar la notificación.',
        'server_unreachable_error': 'Error de red o servidor inaccesible.',
        'proof_of_payment_title': 'Comprobante de Pago',
        'phone_placeholder': 'Número de Teléfono',
        'email_label': 'Correo Electrónico',
        'email_placeholder': 'Correo Electrónico',
        'receipt_label': 'Recibo de Pago (Máx 10MB: png, jpg, webp)',
        'receipt_upload_btn': 'Subir Recibo',
        'submit_proof_btn': 'Enviar Comprobante',
        'verifying_receipt': 'Verificando...',
        'verification_failed_title': 'Verificación Fallida',
        'verification_failed_message': 'Por favor revise el recibo o suba un nuevo recibo.',
        'verification_success_title': 'Verificación Exitosa',
        'verification_success_message': 'Su recibo ha sido verificado. Esperando aprobación del administrador.',
        'back_to_proof_form': 'Atrás',
        'error_uploading_receipt': 'Ocurrió un error al subir el recibo.',
        'error_invalid_file_type': 'Tipo de archivo inválido. Solo puede subir png, jpg, jpeg o webp.',
        'error_file_too_large': 'Archivo demasiado grande. Máximo 10MB.',
        'error_form_incomplete': 'Por favor complete todos los campos y suba un recibo.',
        'error_validation_failed': 'Error de validación del formulario. Por favor verifique los campos.'
    },
    'ja': {
        'payment_options_title': '支払い方法の選択',
        'back_to_subscriptions': 'サブスクリプションに戻る',
        'back_to_select': '戻る',
        'payment_method_qr': 'QRコードで支払う',
        'payment_method_transfer': '送金で支払う',
        'qr_select_title': 'QRコードの選択',
        'transfer_select_title': '送金の詳細',
        'summary_header': '支払いプランの概要',
        'role_label': 'ロール:',
        'duration_label': '期間:',
        'price_label': '支払い金額:',
        'transfer_instructions': '以下の情報を使用して支払いを行ってください。アカウント情報をタップするとコピーできます。',
        'payment_completed_btn': '支払いました',
        'payment_crypto': 'Crypto',
        'payment_famapp': 'FamApp',
        'payment_paytm': 'PayTM',
        'payment_paypal': 'PayPal',
        'copied_to_clipboard': 'クリップボードにコピーしました！',
        'payment_crypto_info': 'デポジット: USDT, ネットワーク: Tron (TRC20)',
		'username_label': 'ユーザー名',
        'intent_recorded_redirecting': '意図が記録されました。リダイレクト中...',
        'payment_notification_sending': '支払い通知を送信中...',
        'payment_notification_success': '支払い通知が成功しました。管理者による承認を待機しています。',
        'payment_notification_error': '通知の送信中にエラーが発生しました。',
        'server_unreachable_error': 'ネットワークエラーまたはサーバーに到達できません。',
        'proof_of_payment_title': '支払い証明',
        'phone_placeholder': '電話番号',
        'email_label': 'メールアドレス',
        'email_placeholder': 'メールアドレス',
        'receipt_label': '支払い領収書 (最大10MB: png, jpg, webp)',
        'receipt_upload_btn': '領収書をアップロード',
        'submit_proof_btn': '証明を送信',
        'verifying_receipt': '確認中...',
        'verification_failed_title': '確認失敗',
        'verification_failed_message': '領収書を確認するか、新しい領収書をアップロードしてください。',
        'verification_success_title': '確認成功',
        'verification_success_message': '領収書が確認されました。管理者による承認を待機しています。',
        'back_to_proof_form': '戻る',
        'error_uploading_receipt': '領収書のアップロード中にエラーが発生しました。',
        'error_invalid_file_type': '無効なファイルタイプです。png、jpg、jpeg、webpのみアップロードできます。',
        'error_file_too_large': 'ファイルが大きすぎます。最大10MB。',
        'error_form_incomplete': 'すべてのフィールドを入力し、領収書をアップロードしてください。',
        'error_validation_failed': 'フォーム検証エラー。フィールドを確認してください。'
    },
    'ko': {
        'payment_options_title': '결제 수단 선택',
        'back_to_subscriptions': '구독으로 돌아가기',
        'back_to_select': '뒤로',
        'payment_method_qr': 'QR 코드로 결제',
        'payment_method_transfer': '송금으로 결제',
        'qr_select_title': 'QR 코드 선택',
        'transfer_select_title': '송금 상세 정보',
        'summary_header': '결제할 플랜 요약',
        'role_label': '역할:',
        'duration_label': '기간:',
        'price_label': '결제 금액:',
        'transfer_instructions': '아래 정보를 사용하여 결제를 진행하십시오. 계좌 정보를 탭하여 복사할 수 있습니다.',
        'payment_completed_btn': '결제 완료',
        'payment_crypto': 'Crypto',
		'username_label': '사용자 이름',
        'payment_famapp': 'FamApp',
        'payment_paytm': 'PayTM',
        'payment_paypal': 'PayPal',
        'copied_to_clipboard': '클립보드에 복사되었습니다!',
        'payment_crypto_info': '입금: USDT, 네트워크: Tron (TRC20)',
        'intent_recorded_redirecting': '의도가 기록되었습니다. 리디렉션 중...',
        'payment_notification_sending': '결제 알림 전송 중...',
        'payment_notification_success': '결제 알림 성공. 관리자 승인 대기 중.',
        'payment_notification_error': '알림 전송 중 오류가 발생했습니다.',
        'server_unreachable_error': '네트워크 오류 또는 서버에 연결할 수 없습니다.',
        'proof_of_payment_title': '결제 증명',
        'phone_placeholder': '전화번호',
        'email_label': '이메일 주소',
        'email_placeholder': '이메일 주소',
        'receipt_label': '결제 영수증 (최대 10MB: png, jpg, webp)',
        'receipt_upload_btn': '영수증 업로드',
        'submit_proof_btn': '증명 제출',
        'verifying_receipt': '확인 중...',
        'verification_failed_title': '확인 실패',
        'verification_failed_message': '영수증을 확인하거나 새 영수증을 업로드하십시오.',
        'verification_success_title': '확인 성공',
        'verification_success_message': '영수증이 확인되었습니다. 관리자 승인 대기 중.',
        'back_to_proof_form': '뒤로',
        'error_uploading_receipt': '영수증 업로드 중 오류가 발생했습니다.',
        'error_invalid_file_type': '잘못된 파일 형식입니다. png, jpg, jpeg, webp만 업로드할 수 있습니다.',
        'error_file_too_large': '파일이 너무 큽니다. 최대 10MB.',
        'error_form_incomplete': '모든 필드를 입력하고 영수증을 업로드하십시오.',
        'error_validation_failed': '폼 검증 오류. 필드를 확인하십시오.'
    },
    'zh': {
        'payment_options_title': '选择支付方式',
        'back_to_subscriptions': '返回订阅',
        'back_to_select': '返回',
        'payment_method_qr': 'QR码支付',
        'payment_method_transfer': '转账支付',
        'qr_select_title': 'QR码选择',
        'transfer_select_title': '转账详情',
        'summary_header': '待支付计划摘要',
        'role_label': '角色:',
        'duration_label': '时长:',
        'price_label': '应付金额:',
        'transfer_instructions': '请使用以下信息进行支付。您可以点击账户详情进行复制。',
        'payment_completed_btn': '我已支付',
        'payment_crypto': 'Crypto',
		'username_label': '您的用户名',
        'payment_famapp': 'FamApp',
        'payment_paytm': 'PayTM',
        'payment_paypal': 'PayPal',
        'copied_to_clipboard': '已复制到剪贴板！',
        'payment_crypto_info': '存款: USDT, 网络: Tron (TRC20)',
        'intent_recorded_redirecting': '意图已记录。正在重定向...',
        'payment_notification_sending': '正在发送支付通知...',
        'payment_notification_success': '支付通知成功。等待管理员批准。',
        'payment_notification_error': '发送通知时发生错误。',
        'server_unreachable_error': '网络错误或服务器无法访问。',
        'proof_of_payment_title': '支付证明',
        'phone_placeholder': '电话号码',
        'email_label': '电子邮件地址',
        'email_placeholder': '电子邮件地址',
        'receipt_label': '支付收据 (最大10MB: png, jpg, webp)',
        'receipt_upload_btn': '上传收据',
        'submit_proof_btn': '提交证明',
        'verifying_receipt': '验证中...',
        'verification_failed_title': '验证失败',
        'verification_failed_message': '请检查收据或上传新的收据。',
        'verification_success_title': '验证成功',
        'verification_success_message': '您的收据已验证。等待管理员批准。',
        'back_to_proof_form': '返回',
        'error_uploading_receipt': '上传收据时发生错误。',
        'error_invalid_file_type': '无效的文件类型。您只能上传png、jpg、jpeg或webp。',
        'error_file_too_large': '文件太大。最大10MB。',
        'error_form_incomplete': '请填写所有字段并上传收据。',
        'error_validation_failed': '表单验证错误。请检查字段。'
    },
    'hi': {
        'payment_options_title': 'भुगतान विधि चुनें',
        'back_to_subscriptions': 'सदस्यता पर वापस जाएं',
        'back_to_select': 'वापस',
        'payment_method_qr': 'QR कोड से भुगतान करें',
        'payment_method_transfer': 'स्थानांतरण भुगतान',
        'qr_select_title': 'QR कोड चयन',
        'transfer_select_title': 'स्थानांतरण विवरण',
        'summary_header': 'भुगतान योजना का सारांश',
        'role_label': 'भूमिका:',
        'duration_label': 'अवधि:',
        'price_label': 'देय राशि:',
        'transfer_instructions': 'कृपया नीचे दी गई जानकारी का उपयोग करके भुगतान करें। आप खाता विवरण पर टैप करके कॉपी कर सकते हैं।',
        'payment_completed_btn': 'मैंने भुगतान कर दिया है',
        'payment_crypto': 'Crypto',
        'payment_famapp': 'FamApp',
        'payment_paytm': 'PayTM',
		'username_label': 'आपका उपयोगकर्ता नाम',
        'payment_paypal': 'PayPal',
        'copied_to_clipboard': 'क्लिपबोर्ड पर कॉपी किया गया!',
        'payment_crypto_info': 'जमा: USDT, नेटवर्क: Tron (TRC20)',
        'intent_recorded_redirecting': 'इरादा दर्ज किया गया। रीडायरेक्ट किया जा रहा है...',
        'payment_notification_sending': 'भुगतान सूचना भेजी जा रही है...',
        'payment_notification_success': 'भुगतान सूचना सफल। व्यवस्थापक की स्वीकृति की प्रतीक्षा है।',
        'payment_notification_error': 'सूचना भेजते समय एक त्रुटि हुई।',
        'server_unreachable_error': 'नेटवर्क त्रुटि या सर्वर अगम्य है।',
        'proof_of_payment_title': 'भुगतान प्रमाण',
        'phone_placeholder': 'आपका फोन नंबर',
        'email_label': 'ईमेल पता',
        'email_placeholder': 'आपका ईमेल पता',
        'receipt_label': 'भुगतान रसीद (अधिकतम 10MB: png, jpg, webp)',
        'receipt_upload_btn': 'रसीद अपलोड करें',
        'submit_proof_btn': 'प्रमाण जमा करें',
        'verifying_receipt': 'सत्यापित किया जा रहा है...',
        'verification_failed_title': 'सत्यापन विफल',
        'verification_failed_message': 'कृपया रसीद जांचें या नई रसीद अपलोड करें।',
        'verification_success_title': 'सत्यापन सफल',
        'verification_success_message': 'आपकी रसीद सत्यापित हो गई है। व्यवस्थापक की स्वीकृति की प्रतीक्षा है।',
        'back_to_proof_form': 'वापस',
        'error_uploading_receipt': 'रसीद अपलोड करते समय एक त्रुटि हुई।',
        'error_invalid_file_type': 'अमान्य फ़ाइल प्रकार। आप केवल png, jpg, jpeg या webp अपलोड कर सकते हैं।',
        'error_file_too_large': 'फ़ाइल बहुत बड़ी है। अधिकतम 10MB।',
        'error_form_incomplete': 'कृपया सभी फ़ील्ड भरें और एक रसीद अपलोड करें।',
        'error_validation_failed': 'फ़ॉर्म सत्यापन त्रुटि। कृपया फ़ील्ड जांचें।'
    }
};

// Global getLang fonksiyonunu genişletiyoruz (script.js'te tanımlı olduğunu varsayarak)
function getLangPayment(key, params = {}) {
    const lang = localStorage.getItem('userLanguage') || 'en';
    
    // 1. Önce paymentTranslations içinde ara
    if (paymentTranslations[lang] && paymentTranslations[lang][key]) {
        return paymentTranslations[lang][key];
    }
    
    // 2. Bulamazsa, ana script.js'teki global getLang'i kullan
    if (typeof getLang === 'function') {
        return getLang(key, params);
    }
    
    return key;
}

function getCSRFToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : ''; 
}

document.addEventListener('DOMContentLoaded', () => {
    
    // Gerekli HTML elementlerini al
    const steps = document.querySelectorAll('.payment-step');
    const step1 = document.getElementById('step1-selection');
    const step2 = document.getElementById('step2-qr');
    const step3 = document.getElementById('step3-transfer');
    
    const qrImageDisplay = document.getElementById('qrImageDisplay');
    const qrInfoText = document.getElementById('qrInfoText');
    const qrMethodGrid = document.getElementById('qrMethodGrid');
    const transferDetailsContainer = document.getElementById('transferDetailsContainer');

    // Sunucudan gelen intent verisi (Jinja'dan tanımlanmıştır)
    const intent = typeof intentData !== 'undefined' ? intentData : {};
    
    // Geçerli adımı ve geri navigasyonu yöneten fonksiyon
    function showStep(targetStepId) {
        steps.forEach(step => step.classList.remove('active'));
        document.getElementById(targetStepId).classList.add('active');
        window.scrollTo(0, 0); // Sayfa değiştirirken üste kaydır
    }

    // --- NAVİGASYON MANTIĞI ---
    // Adım 1'deki kartlara tıklama
    document.querySelectorAll('.method-card').forEach(card => {
        card.addEventListener('click', () => {
            const nextStepId = card.dataset.nextStep;
            showStep(nextStepId);
            // Eğer QR sayfasıysa, QR butonlarını yükle
            if (nextStepId === 'step2-qr') {
                 renderQrButtons();
                 // İlk butonu otomatik seç (Eğer varsa)
                 const firstQrBtn = qrMethodGrid.querySelector('.qr-icon-btn');
                 if (firstQrBtn) firstQrBtn.click();
            }
            // Eğer Transfer sayfasıysa, Transfer detaylarını yükle
            if (nextStepId === 'step3-transfer') {
                renderTransferDetails();
            }
        });
    });

    // Geri butonları
    document.querySelectorAll('.back-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const prevStepId = btn.dataset.prevStep;
            showStep(prevStepId);
        });
    });
    
    // --- QR KOD YÜKLEME MANTIĞI ---
    function renderQrButtons() {
        qrMethodGrid.innerHTML = ''; // Önce temizle
        const details = intent.paymentDetails;
        
        Object.keys(details).forEach(key => {
            const detail = details[key];
            const btn = document.createElement('button');
            btn.className = 'qr-icon-btn';
            btn.dataset.methodKey = key;
            
            // Logo URL'si
            const img = document.createElement('img');
            img.src = detail.logo;
            img.alt = key.toUpperCase() + ' Logo';
            
            // Etiket için span
            const label = document.createElement('span');
            label.textContent = getLangPayment(`payment_${key}`);
            
            // Sıralama: Resim, ardından metin etiketi
            btn.appendChild(img);
            btn.appendChild(label);
            
            btn.addEventListener('click', () => {
                // Seçili butonu işaretle
                document.querySelectorAll('.qr-icon-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                
                // QR Kod resmini göster (images/qr_key.png olduğunu varsayıyoruz)
                qrImageDisplay.src = `/static/images/qr_${key}.png`;
                qrImageDisplay.style.display = 'block';
                
                // Bilgiyi göster (Kripto için özel çeviri kullan)
                const info = key === 'crypto' ? 
                             getLangPayment('payment_crypto_info') : 
                             `${detail.info} ${detail.transfer_value}`;
                             
                qrInfoText.textContent = info;
            });
            qrMethodGrid.appendChild(btn);
        });
    }

// --- TRANSFER DETAYLARI YÜKLEME MANTIĞI ---
function renderTransferDetails() {
    transferDetailsContainer.innerHTML = '';
    const details = intent.paymentDetails;

    Object.keys(details).forEach((key, index) => {
        const detail = details[key];
        const box = document.createElement('div');
        box.className = 'transfer-method-box';

        // Başlık (Logo + İsim)
        const title = document.createElement('h5');
        const img = document.createElement('img');
        img.src = detail.logo;
        img.alt = key.toUpperCase() + ' Logo';
        const labelSpan = document.createElement('span');
        labelSpan.textContent = getLangPayment(`payment_${key}`);
        title.appendChild(img);
        title.appendChild(labelSpan);
        box.appendChild(title);

        // Detay (Ağ bilgisi, UPI ID veya E-MAIL)
        const detailInfo = document.createElement('p');
        // Kripto için özel bilgi metni
        const infoText = key === 'crypto' ? getLangPayment('payment_crypto_info') : detail.info; 
        detailInfo.textContent = infoText;
        box.appendChild(detailInfo);

        // Kopyalanabilir Değer
        const copyDiv = document.createElement('div');
        copyDiv.className = 'transfer-value-display';
        copyDiv.dataset.value = detail.transfer_value; // Kopyalanacak değer

        const valueSpan = document.createElement('span');
        
        // YENİ: Kodu kısaltma mantığı
        const fullValue = detail.transfer_value;
        // Kodu 20 karaktere kısalt ve ... ekle
        if (fullValue.length > 20) {
            valueSpan.textContent = fullValue.substring(0, 20) + "...";
        } else {
            valueSpan.textContent = fullValue;
        }
        
        const icon = document.createElement('i');
        icon.className = 'far fa-copy copy-btn-icon';

        copyDiv.appendChild(valueSpan);
        copyDiv.appendChild(icon);
        
        // Kopyalama Olayı
        copyDiv.addEventListener('click', () => {
            navigator.clipboard.writeText(copyDiv.dataset.value)
                .then(() => {
                    const originalText = valueSpan.textContent; // Orijinal (kısaltılmış) metni sakla

                    // 1. İKON DEĞİŞİKLİĞİ (DÜZELTİLMİŞ)
                    // 'far' (Regular) ve 'fa-copy' ikonunu kaldır
                    icon.classList.remove('far', 'fa-copy');
                    // 'fas' (Solid), 'fa-clipboard-check' ve 'copied' stilini ekle
                    icon.classList.add('fas', 'fa-clipboard-check', 'copied');
                    
                    // 2. METİN DEĞİŞİKLİĞİ
                    valueSpan.classList.add('copied');
                    valueSpan.textContent = getLangPayment('copied_to_clipboard'); 
                    
                    // 2 Saniye sonra eski haline döndür
                    setTimeout(() => {
                        // 3. METNİ GERİ YÜKLE
                        valueSpan.textContent = originalText;
                        
                        // 4. İKONU GERİ YÜKLE (DÜZELTİLMİŞ)
                        // 'fas' (Solid), 'fa-clipboard-check' ve 'copied' stilini kaldır
                        icon.classList.remove('fas', 'fa-clipboard-check', 'copied');
                        // Orijinal 'far' (Regular) ve 'fa-copy' ikonunu geri ekle
                        icon.classList.add('far', 'fa-copy');
                        
                        // 5. METİN STİLİNİ GERİ YÜKLE
                        valueSpan.classList.remove('copied');
                    }, 2000);
                    
                    console.log(getLangPayment('copied_to_clipboard')); 
                })
                .catch(err => {
                    console.error('Kopyalama başarısız:', err);
                });
        });

        box.appendChild(copyDiv);
        transferDetailsContainer.appendChild(box);
    });
}

    // --- Ödeme Onay Butonları MANTIĞI ---
    
    function setupConfirmButton(buttonId, statusDivId) {
        const button = document.getElementById(buttonId);
        
        if (button) {
            button.addEventListener('click', () => {
                // Sunucuya istek atmak yerine, kanıt formunu göster
                showStep('step4-proof');
                
                // Formdaki gizli intent_id'yi ayarla
                const proofForm = document.getElementById('paymentProofForm');
                if (proofForm) {
                    proofForm.querySelector('#form_intent_id').value = intent.id;
                }
                
                // Eski hata mesajlarını temizle
                const statusDiv = document.getElementById('proofPaymentStatus');
                if (statusDiv) {
                    statusDiv.innerHTML = '';
                }
            });
        }
    }
    
    setupConfirmButton('qrPaymentConfirmBtn', 'qrPaymentStatus');
    setupConfirmButton('transferPaymentConfirmBtn', 'transferPaymentStatus');

    // --- YENİ: KANIT YÜKLEME MANTIĞI ---

    const proofForm = document.getElementById('paymentProofForm');
    const receiptFileInput = document.getElementById('receiptFileInput');
    const receiptFileName = document.getElementById('receiptFileName');
    const proofStatusDiv = document.getElementById('proofPaymentStatus');
    const verificationResultDiv = document.getElementById('verificationResult');
    const verificationResultTitle = document.getElementById('verificationResultTitle');
    const verificationResultMessage = document.getElementById('verificationResultMessage');
    const backToProofBtn = document.getElementById('backToProofBtn');

    // Dekont yükleme butonu
    document.getElementById('receiptUploadBtn').addEventListener('click', () => {
        receiptFileInput.click();
    });

    // Dekont dosya seçimi
    receiptFileInput.addEventListener('change', () => {
        if (receiptFileInput.files.length > 0) {
            const file = receiptFileInput.files[0];
            const allowedTypes = ['image/png', 'image/jpeg', 'image/webp'];
            
            // Client-side dosya boyutu kontrolü
            if (file.size > 10 * 1024 * 1024) { // 10 MB
                receiptFileName.textContent = getLangPayment('error_file_too_large');
                receiptFileName.style.color = 'var(--color-accent-red)';
                receiptFileInput.value = ''; // Seçimi sıfırla
                return;
            }
            
            // Client-side dosya tipi kontrolü
            if (!allowedTypes.includes(file.type)) {
                receiptFileName.textContent = getLangPayment('error_invalid_file_type');
                receiptFileName.style.color = 'var(--color-accent-red)';
                receiptFileInput.value = ''; // Seçimi sıfırla
                return;
            }

            receiptFileName.textContent = file.name;
            receiptFileName.style.color = 'var(--color-accent-green)';
        } else {
            receiptFileName.textContent = '';
        }
    });

// Kanıt formu gönderme
proofForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // GÜNCELLENDİ: Sadece email ve dosya kontrolü (Kullanıcı adı readonly)
    const email = document.getElementById('email').value;
    const file = receiptFileInput.files[0];

    if (!email || !file) {
        proofStatusDiv.innerHTML = `<p class="flash-danger">${getLangPayment('error_form_incomplete')}</p>`;
        return;
    }
    
    // Yükleniyor ekranını göster
    showStep('step5-verifying');
    proofStatusDiv.innerHTML = ''; 

    const formData = new FormData(proofForm);

    try {
        const response = await fetch('/submit_payment_proof', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            },
            body: formData
        });

        const data = await response.json();

        // --- 429 HATA KONTROLÜ ---
        if (response.status === 429 && data.error === 'TOO_MANY_ATTEMPTS') {
            const totalSeconds = data.remaining_time_seconds;
            const hours = Math.floor(totalSeconds / 3600);
            const minutes = Math.floor((totalSeconds % 3600) / 60);
            let remainingTimeString = "";
            if (hours > 0) remainingTimeString += `${hours}s `;
            remainingTimeString += `${minutes}dk`;

            const errorMsg = getLang('too_many_receipt_attempts', { time: remainingTimeString });

            // Hata mesajını göster
            showToast(errorMsg, 'error');
            
            // 3 saniye sonra abonelikler sayfasına yönlendir
            setTimeout(() => {
                window.location.href = '/subscriptions';
            }, 3000);
            return;
        }

        showStep('step6-verification-result'); 

        if (response.ok && data.success) {
            if (data.verified) {
                verificationResultTitle.textContent = getLangPayment('verification_success_title');
                verificationResultMessage.textContent = getLangPayment('verification_success_message');
                backToProofBtn.style.display = 'none'; 
                document.getElementById('verificationIcon').className = 'fas fa-check-circle icon-success';
            } else {
                verificationResultTitle.textContent = getLangPayment('verification_failed_title');
                verificationResultMessage.textContent = getLangPayment('verification_failed_message');
                backToProofBtn.style.display = 'block'; 
                document.getElementById('verificationIcon').className = 'fas fa-times-circle icon-danger';
            }
        } else {
            verificationResultTitle.textContent = getLangPayment('verification_failed_title');
            verificationResultMessage.textContent = data.error || getLangPayment('error_uploading_receipt');
            backToProofBtn.style.display = 'block';
            document.getElementById('verificationIcon').className = 'fas fa-times-circle icon-danger';
        }

    } catch (error) {
        console.error('Kanıt gönderme hatası:', error);
        showStep('step6-verification-result');
        verificationResultTitle.textContent = getLangPayment('verification_failed_title');
        verificationResultMessage.textContent = getLangPayment('server_unreachable_error');
        backToProofBtn.style.display = 'block';
        document.getElementById('verificationIcon').className = 'fas fa-times-circle icon-danger';
    }
});

    // Doğrulama başarısız olduğunda forma geri dön butonu
    backToProofBtn.addEventListener('click', () => {
        showStep('step4-proof'); // Kanıt formuna geri dön
    });

    // --- DİL ÇEVİRİLERİNİ UYGULAMA ---
    function applyTranslations() {
        // Tüm çeviri anahtarlarını uygula
        document.querySelectorAll('[data-lang-key]').forEach(elem => {
            const key = elem.getAttribute('data-lang-key');
            const translatedText = getLangPayment(key);
            
            if (translatedText !== key) {
                // INPUT veya TEXTAREA değilse textContent kullan
                if (elem.tagName !== 'INPUT' && elem.tagName !== 'TEXTAREA') {
                    elem.textContent = translatedText;
                } else {
                    // INPUT veya TEXTAREA ise placeholder veya value'yu güncelle
                    if (elem.placeholder !== undefined) {
                        elem.placeholder = translatedText;
                    } else {
                        elem.value = translatedText;
                    }
                }
            }
        });
        
        // Aktif sayfaya göre özel güncellemeler yap
        const activeStep = document.querySelector('.payment-step.active');
        if (activeStep && activeStep.id === 'step3-transfer') {
            renderTransferDetails();
        }
        if (activeStep && activeStep.id === 'step2-qr') {
            renderQrButtons();
        }
    }

    // İlk yüklemede çevirileri uygula
    applyTranslations();
    
    // Dil değiştiğinde çevirileri güncelle
    document.addEventListener('languageChanged', () => {
        applyTranslations();
    });

    // Sayfa ilk açıldığında dil değişim event'ini tetikle
    document.dispatchEvent(new CustomEvent('languageChanged'));
});