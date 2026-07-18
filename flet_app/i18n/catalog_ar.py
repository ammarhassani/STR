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
    "common.no_entity": "(بدون جهة)",
    "common.reviewer": "المُراجع",
    "common.loading": "جارٍ التحميل...",

    # My Work
    "mywork.lane.rework": "أُعيدت لإعادة العمل",
    "mywork.lane.draft": "المسودّات",
    "mywork.lane.pending": "قيد الاعتماد",
    "mywork.lane.approved": "معتمدة",
    "mywork.nothing": "لا يوجد شيء هنا.",

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
    "nav.activity": "سجل النشاط",

    # header actions
    "header.new_report": "تقرير جديد",
    "header.refresh": "تحديث",
    "header.help": "مساعدة",
    "header.profile": "ملفي الشخصي",
    "header.backup": "النسخ الاحتياطي والاستعادة",
    "header.reservations": "أرقامي",
    "header.logout": "تسجيل الخروج",
    "header.notifications": "الإشعارات",
    "header.admin_tools": "أدوات المشرف",
    "header.reservation_mgmt": "إدارة الأرقام",

    # dashboard
    "dash.welcome": "مرحباً بعودتك، {name}!",
    "dash.refresh": "تحديث",
    "dash.recent_activity": "النشاط الأخير",
    "dash.view_all": "عرض الكل",
    "dash.no_activity": "لا يوجد نشاط حديث",
    "dash.loading": "جارٍ تحميل لوحة المعلومات...",
    "dash.loading_activity": "جارٍ تحميل النشاط...",
    "dash.loading_widgets": "جارٍ تحميل العناصر...",
    "dash.no_widgets": "لا توجد عناصر مُهيّأة للوحة.",
    "dash.nav_activity_hint": "انتقل إلى سجل النشاط من الشريط الجانبي",
}
