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
    "common.actions": "إجراءات",
    "common.search": "بحث",
    "common.refresh": "تحديث",
    "common.view": "عرض",

    # approval status
    "status.draft": "مسودة",
    "status.pending_approval": "قيد الاعتماد",
    "status.approved": "معتمد",
    "status.rejected": "مرفوض",
    "status.rework": "إعادة عمل",

    # reports list
    "reports.add_new": "إضافة تقرير جديد",
    "reports.search": "بحث:",
    "reports.search_hint": "ابحث برقم التقرير أو الجهة أو رقم CIC...",
    "reports.none": "لا توجد تقارير",
    "reports.loading": "جارٍ تحميل التقارير...",

    # My Work
    "mywork.lane.rework": "أُعيدت لإعادة العمل",
    "mywork.lane.draft": "المسودّات",
    "mywork.lane.pending": "قيد الاعتماد",
    "mywork.lane.approved": "معتمدة",
    "mywork.nothing": "لا يوجد شيء هنا.",

    # report field labels not in column_settings (derived/special)
    "field.case_id": "رقم الحالة",
    "field.id_type": "نوع الهوية/السجل",
    "field.relationship": "العلاقة",

    # report form: tabs + buttons
    "form.tab.basic": "المعلومات الأساسية",
    "form.tab.entity": "تفاصيل الجهة",
    "form.tab.suspicion": "تفاصيل الاشتباه",
    "form.tab.classification": "التصنيف والمصدر",
    "form.tab.fiu": "تفاصيل وحدة التحريات",
    "form.save": "حفظ التقرير",
    "form.submit": "إرسال للاعتماد",
    "form.view_history": "عرض السجل",
    "form.new_title": "إضافة تقرير جديد",
    "form.edit_title": "تعديل التقرير",
    "form.success": "تم بنجاح",
    "form.chk.legal_owner": "مالك الكيان القانوني",
    "form.chk.is_cr": "سجل تجاري (CR)",
    "form.chk.is_membership": "عضوية؟",
    "form.hint.sn": "أدخل الرقم التسلسلي (مثال: 1)",
    "form.hint.report_number": "الصيغة: YYYY/MM/NNN (مثال: 2025/11/001)",
    "form.hint.case_id": "أدخل رقم الحالة (اختياري)",
    "form.hint.date": "يوم/شهر/سنة",
    "form.hint.date_optional": "يوم/شهر/سنة (اختياري)",
    "form.hint.entity": "أدخل اسم الجهة",
    "form.hint.id_cr": "أدخل رقم الهوية أو السجل التجاري",
    "form.hint.account": "أدخل رقم الحساب أو العضوية",
    "form.hint.branch": "أدخل رقم الفرع",
    "form.hint.cic": "أدخل رقم CIC (سيُكمَّل تلقائياً إلى 16 رقماً)",
    "form.hint.first_reason": "صف السبب الأول للاشتباه",
    "form.hint.second_reason": "صف السبب الثاني للاشتباه",
    "form.hint.total": "أدخل المبلغ بالريال (مثال: 605040 SAR)",
    "form.hint.initials": "أدخل حرفين كبيرين (مثال: ZM)",
    "form.hint.fiu_number": "أدخل رقم وحدة التحريات",
    "form.hint.fiu_letter": "أدخل رقم خطاب الوحدة",
    "form.err.login_first": "الرجاء تسجيل الدخول أولاً.",
    "form.err.no_create": "لا يسمح دورك بإنشاء التقارير.",
    "form.err.no_reserved": "لا توجد لديك أرقام محجوزة — احجز أرقاماً أولاً (Ctrl+R).",

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
