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

    # approval panel
    "appr.showing": "عرض {n} طلب اعتماد قيد الانتظار",
    "appr.none": "لا توجد طلبات اعتماد قيد الانتظار حالياً.",
    "appr.review": "مراجعة",
    "appr.col.report": "رقم التقرير",
    "appr.col.entity": "اسم الجهة",
    "appr.col.requested_by": "طلب بواسطة",
    "appr.col.requested_at": "تاريخ الطلب",
    "appr.col.status": "الحالة",
    "appr.col.comment": "تعليق",
    "appr.pending": "قيد الانتظار",
    "appr.your_decision": "قرارك",
    "appr.opt.approve": "اعتماد - التقرير دقيق ومكتمل",
    "appr.opt.rework": "طلب إعادة عمل - إعادته للتصحيح",
    "appr.opt.reject": "رفض - التقرير غير صالح",
    "appr.opt.edit": "تعديل - عدّل حقول التقرير بنفسك",
    "appr.comment": "تعليق القرار (مطلوب لإعادة العمل/الرفض)",
    "appr.comment_hint": "أدخل الملاحظات أو أسباب هذا القرار...",
    "appr.reassign": "إعادة تعيين إعادة العمل إلى (اختياري)",
    "appr.keep_agent": "إبقاء الموظف الحالي",
    "appr.keep_agent_opt": "-- إبقاء الموظف الحالي --",
    "appr.save_changes": "حفظ التغييرات",
    "appr.approve_report": "اعتماد التقرير",
    "appr.loading": "جارٍ تحميل بيانات التقرير...",
    "appr.edit_enabled": "تم تفعيل وضع التعديل. يمكنك الآن تعديل حقول النموذج.",

    # roles + filters
    "role.admin": "مدير",
    "role.supervisor": "مشرف",
    "role.agent": "موظف",
    "role.reporter": "مُبلِّغ",
    "filter.all_roles": "كل الأدوار",
    "filter.all": "الكل",
    "filter.role": "الدور:",
    "filter.status": "الحالة:",

    # user management
    "users.title": "إدارة المستخدمين",
    "users.add": "إضافة مستخدم جديد",
    "users.none": "لا يوجد مستخدمون",
    "users.col.id": "المعرّف",
    "users.col.username": "اسم المستخدم",
    "users.col.fullname": "الاسم الكامل",
    "users.col.role": "الدور",
    "users.col.status": "الحالة",
    "users.col.last_login": "آخر دخول",
    "users.status.pending": "بانتظار التسجيل",
    "users.status.active": "نشط",
    "users.status.inactive": "غير نشط",
    "users.never": "أبداً",
    "users.edit_tip": "تعديل المستخدم",
    "users.delete_tip": "حذف المستخدم",
    "users.confirm_delete": "تأكيد الحذف",
    "users.count": "{n} مستخدم",

    # user dialog
    "udlg.edit": "تعديل المستخدم",
    "udlg.add": "إضافة مستخدم جديد",
    "udlg.user_id": "معرّف المستخدم *",
    "udlg.user_id_hint": "مثال: reporter7 (يسجّل المستخدم الدخول به)",
    "udlg.fullname": "الاسم الكامل (يحدده المستخدم)",
    "udlg.awaiting": "بانتظار التسجيل عند أول دخول",
    "udlg.registered": "مُسجَّل — كلمة المرور يحددها المستخدم",
    "udlg.role": "الدور *",
    "udlg.status": "الحالة",
    "udlg.handshake_note": "يحدد المستخدم اسمه وكلمة مروره عند أول تسجيل دخول.",
    "udlg.reset_pw": "إعادة تعيين كلمة المرور",
    "udlg.err_userid": "معرّف المستخدم مطلوب",

    # settings
    "set.title": "إعدادات النظام",
    "set.info": "اضبط الإعدادات العامة للنظام. تسري التغييرات فور الحفظ.",
    "set.group.numbering": "ترقيم التقارير",
    "set.group.batch": "الحجز الجماعي",
    "set.group.general": "عام",
    "set.numbering_help": "يتبع الترقيم الشهر الميلادي تلقائياً — يبدأ تسلسل جديد (من 001) عند تغيّر الشهر. الأرقام التي حجزتها تحتفظ بشهرها وتبقى لك حتى تستخدمها أو تنقلها.",
    "set.batch_pool": "حجم مجموعة الحجز:",
    "set.batch_pool_hint": "أرقام تقارير محجوزة مسبقاً في المجموعة. أكبر = أسرع للمستخدمين المتزامنين. المقترح: 10-30",
    "set.expiry": "انتهاء صلاحية الحجز:",
    "set.expiry_hint": "المدة قبل انتهاء صلاحية الأرقام المحجوزة. أطول = مرونة أكثر. المقترح: 5-10 دقائق",
    "set.page_size": "حجم الصفحة الافتراضي:",
    "set.page_size_hint": "عدد السجلات المعروضة في كل صفحة بالجداول",
    "set.suffix_records": "سجل",
    "set.suffix_minutes": "دقيقة",
    "set.reset": "إعادة للافتراضي",
    "set.save": "حفظ الإعدادات",

    # reservation dialog
    "res.title": "أرقام تقاريري",
    "res.count": "العدد",
    "res.select_all": "تحديد الكل",
    "res.transfer_to": "نقل إلى",
    "res.none": "لا توجد أرقام متاحة. احجز بعضها أعلاه.",
    "res.have": "لديك {n} رقم متاح.",
    "res.received_from": "مستلَم من {user}",
    "res.transfer_selected": "نقل الأرقام المحددة",
    "res.reserve": "حجز",
    "res.transfer": "نقل",
    "res.err_recipient": "اختر مستلِماً.",
    "res.err_select": "اختر رقماً واحداً على الأقل للنقل.",

    # change password
    "cpw.title": "تغيير كلمة المرور",
    "cpw.current": "كلمة المرور الحالية",
    "cpw.new": "كلمة المرور الجديدة",
    "cpw.confirm": "تأكيد كلمة المرور الجديدة",
    "cpw.strong": "كلمة مرور قوية",
    "cpw.weak": "ضعيفة: {feedback}",
    "cpw.err.current": "الرجاء إدخال كلمة المرور الحالية.",
    "cpw.err.new": "الرجاء إدخال كلمة مرور جديدة.",
    "cpw.err.confirm": "الرجاء تأكيد كلمة المرور الجديدة.",
    "cpw.err.length": "يجب أن تتكوّن كلمة المرور من 8 أحرف على الأقل.",
    "cpw.err.upper": "يجب أن تحتوي كلمة المرور على حرف كبير واحد على الأقل.",
    "cpw.err.lower": "يجب أن تحتوي كلمة المرور على حرف صغير واحد على الأقل.",
    "cpw.err.digit": "يجب أن تحتوي كلمة المرور على رقم واحد على الأقل.",
    "cpw.err.match": "كلمتا المرور الجديدتان غير متطابقتين.",
    "cpw.err.same": "يجب أن تختلف كلمة المرور الجديدة عن الحالية.",

    # help dialog
    "help.title": "المساعدة والتوثيق",
    "help.tab.getting_started": "البدء",
    "help.tab.shortcuts": "الاختصارات",
    "help.tab.faq": "الأسئلة الشائعة",
    "help.tab.about": "حول",
    # DRAFT — pending owner review of FIU terminology.
    "help.body.getting_started": """
## مرحبًا بك في نظام إدارة تقارير وحدة التحرّيات المالية

يساعدك هذا النظام على إدارة تقارير وحدة التحرّيات المالية (FIU) ومتابعتها بكفاءة.

### دليل البدء السريع

1. **لوحة المعلومات** — عرض الملخّص اليومي ومؤشرات الأداء والرسوم البيانية
2. **التقارير** — إنشاء التقارير وتعديلها وإدارتها
3. **التصدير** — تصدير التقارير إلى ملف Excel
4. **الإعدادات** — ضبط إعدادات النظام (للمسؤول فقط)

### إنشاء تقرير

1. اضغط "تقرير جديد" في شريط الأدوات
2. عبّئ الحقول المطلوبة (المعلّمة بـ *)
3. اضغط "حفظ" للحفظ كمسودة أو "إرسال للاعتماد"

### تحتاج مساعدة؟

تواصل مع مسؤول النظام للحصول على المساعدة.
""",
    "help.body.shortcuts": """
## اختصارات لوحة المفاتيح

### إجراءات عامة
| الاختصار | الإجراء |
|----------|--------|
| F1 | فتح المساعدة |
| F5 | تحديث الشاشة الحالية |
| Ctrl+N | تقرير جديد (عند توفّر الصلاحية) |
| Ctrl+P | ملفي الشخصي |
| Escape | إغلاق النافذة المفتوحة |

### اختصارات المسؤول فقط
| الاختصار | الإجراء |
|----------|--------|
| Ctrl+B | النسخ الاحتياطي والاستعادة |
| Ctrl+R | إدارة الحجوزات |

### التنقّل
استخدم الشريط الجانبي للتنقّل بين أقسام التطبيق.

### تلميحات
- استخدم أزرار شريط الأدوات للإجراءات السريعة
- اضغط مبدّل المظهر للتبديل بين الوضع الفاتح والداكن
- مرّر المؤشر فوق الأزرار لعرض التلميحات
""",
    "help.body.faq": """
## الأسئلة الشائعة

### س: كيف أنشئ تقريرًا جديدًا؟
اضغط زر "تقرير جديد" في شريط الأدوات أو اضغط Ctrl+N.

### س: كيف أصدّر التقارير؟
انتقل إلى قسم التصدير من الشريط الجانبي واختر عوامل التصفية.

### س: ما هي حالات التقرير؟
- **مفتوح**: التقرير قيد الإعداد
- **مراجعة الحالة**: بانتظار المراجعة الأولية
- **قيد التحقيق**: جارٍ التحقيق فيه
- **تدقيق الحالة**: مرحلة التدقيق النهائي
- **إغلاق الحالة**: أُغلقت الحالة دون رفع تقرير اشتباه
- **مغلقة برفع تقرير اشتباه**: أُغلقت الحالة مع رفع تقرير اشتباه

### س: كيف أغيّر كلمة المرور؟
اضغط أيقونة الملف الشخصي > ملفي الشخصي > تبويب الأمان > تغيير كلمة المرور

### س: من يستطيع اعتماد التقارير؟
المستخدمون بدور المسؤول فقط يمكنهم اعتماد التقارير.
""",
    "help.about.name": "نظام إدارة تقارير وحدة التحرّيات المالية",
    "help.about.version": "الإصدار 2.0.0 (نسخة Flet)",
    "help.about.blurb": "نظام متكامل لإدارة تقارير وحدة التحرّيات المالية.\nمبني بلغة Python وإطار Flet لتطبيقات سطح المكتب متعددة المنصّات.",
    "help.about.stack": "التقنيات المستخدمة",

    # export view
    "exp.title": "تصدير التقارير إلى Excel",
    "exp.info": "صدّر تقاريرك بصيغة Excel (.xlsx) للتحليل في Excel أو أدوات أخرى. طبّق المرشحات لتصدير تقارير محددة فقط.",
    "exp.filters": "مرشحات التصدير",
    "exp.output": "موقع الحفظ",
    "exp.enable_date": "تفعيل مرشح التاريخ",
    "exp.browse": "استعراض...",
    "exp.browse_prompt": "اختر مجلد الحفظ",
    "exp.err_location": "الرجاء اختيار موقع الحفظ.",
    "exp.err_dir": "مجلد الحفظ المحدد غير موجود.",
    "exp.starting": "جارٍ بدء التصدير...",
    "exp.success": "تم التصدير بنجاح",
    "exp.no": "لا",
    "exp.open_folder": "فتح المجلد",
    "exp.no_filters": "لم تُطبّق مرشحات",
    "exp.all_statuses": "كل الحالات",
    "exp.preview": "معاينة العدد",
    "exp.export": "تصدير إلى Excel",

    # activity log
    "act.title": "سجل النشاط",
    "act.none": "لا يوجد نشاط",
    "act.loading": "جارٍ تحميل الأنشطة...",
    "act.action_type": "نوع الإجراء",
    "act.date_filter": "مرشح التاريخ",

    # dashboard widgets management
    "wm.title": "عناصر اللوحة",
    "wm.none": "لا توجد عناصر بعد. أضف واحداً.",
    "wm.add": "إضافة عنصر",
    "wm.delete_widget": "حذف العنصر",
    "wm.confirm_delete": "حذف '{title}'؟ لا يمكن التراجع.",
    "wm.edit_widget": "تعديل العنصر",
    "wm.add_widget": "إضافة عنصر",
    "wm.type": "نوع العنصر",
    "wm.field_title": "العنوان",
    "wm.sql": "استعلام SQL (قراءة فقط SELECT)",
    "wm.test": "اختبار الاستعلام",
    "wm.color": "اللون (#hex)",
    "wm.icon": "الأيقونة (لبطاقات KPI فقط)",
    "wm.order": "الترتيب",
    "wm.roles": "مرئي للأدوار:",
    "wm.active": "نشط",

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

    # dropdown management
    "ddm.title": "إدارة القوائم المنسدلة",
    "ddm.info": "أدر قيم القوائم المنسدلة لمختلف الحقول. الفئات [القابلة للتعديل] يمكن تعديلها بحرية.",
    "ddm.category": "الفئة:",
    "ddm.select_category": "-- اختر فئة --",
    "ddm.none": "لا توجد قيم",
    "ddm.col.value": "القيمة",
    "ddm.col.order": "الترتيب",
    "ddm.col.status": "الحالة",
    "ddm.col.updated_by": "حُدّث بواسطة",
    "ddm.select_prompt": "اختر فئة لعرض قيمها",
    "ddm.value": "القيمة",
    "ddm.value_en": "القيمة (إنجليزي)",
    "ddm.value_ar": "القيمة (عربي)",
    "ddm.value_ar_hint": "تُعرض العربية في وضع اللغة العربية. اتركها فارغة لاستخدام القيمة الإنجليزية.",
    "ddm.col.value_ar": "القيمة (عربي)",
    "ddm.add_value": "إضافة قيمة",
    "ddm.edit_value": "تعديل قيمة",
    "ddm.display_order": "ترتيب العرض",
    "ddm.err_empty": "لا يمكن أن تكون القيمة فارغة",
    "ddm.order_hint": "الأرقام الأصغر تظهر أولاً",
    "ddm.confirm_delete": "تأكيد الحذف",
    "ddm.restore": "استعادة",
    "ddm.category_label": "الفئة: {cat}",

    # field management
    "fld.title": "إدارة الحقول",
    "fld.info": "اضبط قواعد التحقق وحالة الإلزام لجميع حقول التقرير. ",
    "fld.info2": "تُطبَّق هذه القواعد عند إنشاء التقارير أو تعديلها.",
    "fld.none": "لا توجد إعدادات حقول",
    "fld.col.name": "اسم الحقل",
    "fld.col.required": "مطلوب",
    "fld.col.validation": "قواعد التحقق",
    "fld.col.updated_by": "حُدّث بواسطة",
    "fld.required": "مطلوب",
    "fld.mark_required": "اجعل هذا الحقل مطلوباً",
    "fld.length": "الطول (أرقام)",
    "fld.id_starts": "تبدأ الهوية السعودية بـ",
    "fld.cr_starts": "يبدأ السجل التجاري بـ",
    "fld.idcr_rules": "قواعد التحقق للهوية/السجل",
    "fld.account_length": "طول رقم الحساب",
    "fld.membership_length": "طول رقم العضوية",
    "fld.acc_rules": "قواعد التحقق للحساب/العضوية",

    # backup & restore
    "bak.title": "النسخ الاحتياطي واستعادة قاعدة البيانات",
    "bak.info": "أنشئ نسخاً احتياطية للحماية من فقدان البيانات. استعد من أي نسخة للعودة إلى حالة سابقة.",
    "bak.actions": "إجراءات النسخ الاحتياطي",
    "bak.create_now": "إنشاء نسخة احتياطية الآن",
    "bak.existing": "النسخ الاحتياطية الموجودة",
    "bak.refresh": "تحديث القائمة",
    "bak.none": "لا توجد نسخ احتياطية",
    "bak.create": "إنشاء نسخة احتياطية",
    "bak.create_confirm": "إنشاء نسخة احتياطية من قاعدة البيانات الحالية؟",
    "bak.created": "تم إنشاء النسخة: {name}",
    "bak.restore": "استعادة",
    "bak.restore_title": "⚠️ استعادة قاعدة البيانات",
    "bak.restore_warning": "تحذير: ستستبدل قاعدة بياناتك الحالية!",
    "bak.restore_note": "ستُفقد كل التغييرات منذ هذه النسخة.\nستُنشأ نسخة احتياطية من قاعدتك الحالية أولاً.",
    "bak.restore_confirm": "هل أنت متأكد تماماً من المتابعة؟",
    "bak.restored": "تمت استعادة قاعدة البيانات! الرجاء إعادة تشغيل التطبيق.",
    "bak.delete_title": "حذف النسخة الاحتياطية",
    "bak.delete_confirm": "حذف النسخة: {name}؟\n\nلا يمكن التراجع.",
    "bak.deleted": "تم حذف النسخة الاحتياطية.",

    # version history
    "vh.title": "سجل الإصدارات",
    "vh.tab.versions": "الإصدارات",
    "vh.tab.activity": "النشاط",
    "vh.no_versions": "لا يوجد سجل إصدارات",
    "vh.no_activity": "لا يوجد نشاط مسجّل",
    "vh.no_description": "بدون وصف",
    "vh.version_n": "الإصدار {n}",
    "vh.compare": "مقارنة ({n}/2)",
    "vh.restore": "استعادة",
    "vh.restore_tip": "الاستعادة إلى هذا الإصدار",
    "vh.confirm_restore": "تأكيد الاستعادة",
    "vh.restore_confirm": "هل أنت متأكد من الاستعادة إلى الإصدار {n}؟\n\nسيُنشأ إصدار جديد بالبيانات المستعادة.\nسيُحفظ الإصدار الحالي في السجل.",
    "vh.show_deleted": "عرض المحذوفة",
    "vh.no_service": "خدمة الإصدارات غير متاحة",

    # user profile
    "prof.tab.profile": "الملف الشخصي",
    "prof.tab.activity": "النشاط",
    "prof.tab.security": "الأمان",
    "prof.basic_info": "المعلومات الأساسية",
    "prof.account_info": "معلومات الحساب",
    "prof.activity_stats": "إحصائيات النشاط",
    "prof.recent_activity": "النشاط الأخير",
    "prof.password_auth": "كلمة المرور والمصادقة",
    "prof.session_info": "معلومات الجلسة",
    "prof.fullname": "الاسم الكامل",
    "prof.username": "اسم المستخدم",
    "prof.role": "الدور",
    "prof.account_created": "أُنشئ الحساب:",
    "prof.last_login": "آخر دخول:",
    "prof.total_logins": "إجمالي مرات الدخول:",
    "prof.reports_created": "التقارير المُنشأة:",
    "prof.reports_edited": "التقارير المُعدّلة:",
    "prof.last_activity": "آخر نشاط:",
    "prof.change_password": "تغيير كلمة المرور",
    "prof.save_changes": "حفظ التغييرات",
    "prof.err_fullname": "الاسم الكامل مطلوب.",
    "prof.loading_activity": "جارٍ تحميل النشاط الأخير...",

    # host-down banner (client mode)
    "hostbanner.offline": "المضيف غير متصل — للقراءة فقط. تُدرَج الإدخالات الجديدة في قائمة الانتظار وتُزامَن عند عودة المضيف ({n} قيد الانتظار).",

    # setup wizard
    "wiz.step.welcome": "الترحيب",
    "wiz.step.paths": "إعداد المسارات",
    "wiz.step.database": "إنشاء قاعدة البيانات",
    "wiz.step.complete": "اكتمل",
    "wiz.back": "→ رجوع",
    "wiz.next": "التالي ←",
    "wiz.finish": "إنهاء",
    "wiz.welcome_title": "مرحباً بك في نظام إدارة تقارير وحدة التحريات المالية",
    "wiz.will_configure": "ستقوم بإعداد:",
    "wiz.cfg.db": "موقع قاعدة البيانات",
    "wiz.cfg.backup": "مجلد النسخ الاحتياطي",
    "wiz.cfg.settings": "الإعدادات الأولية للنظام",
    "wiz.db_path": "مسار ملف قاعدة البيانات",
    "wiz.backup_dir": "مجلد النسخ الاحتياطي",
    "wiz.mode.local": "جهاز واحد (قاعدة بيانات محلية)",
    "wiz.mode.host": "جهاز مضيف (يخدم الفريق عبر المجلد المشترك)",
    "wiz.mode.client": "جهاز عميل (يتصل بمضيف عبر المجلد المشترك)",
    "wiz.share_path": "مسار المجلد المشترك (مضيف/عميل)",
    "wiz.db_location": "موقع ملف قاعدة البيانات",
    "wiz.share_folder": "مسار المجلد المشترك",
    "wiz.deploy_mode": "وضع النشر",
    "wiz.browse": "استعراض...",
    "wiz.complete_title": "اكتمل الإعداد بنجاح!",
    "wiz.err_share": "مسار المجلد المشترك غير موجود أو غير قابل للوصول.",
    "wiz.db_exists": "قاعدة البيانات موجودة",
}
