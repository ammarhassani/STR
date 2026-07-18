"""Arabic strings (#3). DRAFT — machine/domain-assisted, pending owner review of
FIU/AML terminology. Keys mirror catalog_en.py; any missing key falls back to
English at runtime."""
STRINGS = {
    # app / common
    "app.title": "نظام الإبلاغ",
    "common.cancel": "إلغاء",
    "common.save": "حفظ",
    "common.close": "إغلاق",
    "common.delete": "حذف",
    "common.edit": "تعديل",
    "common.add": "إضافة",

    # login
    "login.title": "تسجيل الدخول",
    "login.user_id": "معرّف المستخدم",
    "login.password": "كلمة المرور",
    "login.button": "دخول",
    "login.err.enter_user_id": "الرجاء إدخال معرّف المستخدم",
    "login.err.enter_password": "الرجاء إدخال كلمة المرور",
    "login.err.invalid": "اسم المستخدم أو كلمة المرور غير صحيحة",

    # onboarding (two-way handshake)
    "onboard.title": "مرحباً — أكمل تسجيلك",
    "onboard.user_id": "معرّف المستخدم: {username}",
    "onboard.instruction": "عيّن اسمك وكلمة مرور تعرفها أنت وحدك.",
    "onboard.full_name": "الاسم الكامل",
    "onboard.new_password": "كلمة مرور جديدة",
    "onboard.confirm_password": "تأكيد كلمة المرور",
    "onboard.submit": "إتمام التسجيل",
    "onboard.err.name": "الرجاء إدخال اسمك الكامل.",
    "onboard.err.pw_len": "يجب أن تتكوّن كلمة المرور من 8 أحرف على الأقل.",
    "onboard.err.mismatch": "كلمتا المرور غير متطابقتين.",

    # settings
    "settings.language": "اللغة",
    "settings.language.saved": "تم تحديث اللغة. بعض الشاشات تطبّقها بعد إعادة فتحها.",

    # navigation
    "nav.dashboard": "لوحة المعلومات",
    "nav.reports": "التقارير",
    "nav.my_work": "مهامي",
    "nav.export": "تصدير",
    "nav.approvals": "الاعتمادات",
    "nav.users": "المستخدمون",
    "nav.logs": "سجلات النظام",
    "nav.settings": "الإعدادات",
    "nav.dropdowns": "القوائم المنسدلة",
    "nav.fields": "الحقول",
    "nav.widgets": "عناصر اللوحة",
}
