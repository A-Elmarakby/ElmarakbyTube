# ==========================================
# APP MESSAGES & TEXT CONFIGURATION
# ==========================================
# Use this file to translate or change any text in the app.

# ------------------------------------------
# 1. Fonts and Text Sizes (Typography)
# ------------------------------------------
FONT_FAMILY = "Segoe UI"
FONT_SIZE_MAIN = 14
FONT_SIZE_LARGE = 16
FONT_SIZE_POPUP_TITLE = 20
FONT_SIZE_POPUP_BODY = 15

# ------------------------------------------
# 2. Common Buttons (Used across multiple popups)
# ------------------------------------------
BTN_OK = "تمام"
BTN_YES = "آه طبعًا"
BTN_NO = "لا شكرًا" 
BTN_FAST = "في السريع"
BTN_SLOW = "على الهادي"
BTN_CANCEL = "إلغي الحوار ده"

# ------------------------------------------
# 3. Popup Window Titles
# ------------------------------------------
TITLE_ERROR = "خطأ"
TITLE_WARNING = "خد بالك!!"
TITLE_SPEED = "سرعة التحويل ⚡"
TITLE_CONFIRM = "تأكيد"
TITLE_ERROR_DETAILS = "تفاصيل المشكلة"
TITLE_ALERT = "تنبيه"

# ------------------------------------------
# 4. Core System Messages & Warnings
# ------------------------------------------
# User forgot to pick video quality.
MSG_QUALITY_MISSING = "نسيت تختار الجودة اللي أنت عايزها؟\nحدّد الجودة من المربع اللي فوق قبل ما تحمّل أو تحسب الحجم."

# User did not select any video to fetch size.
MSG_NO_VIDEO_FETCH = "اختار فيديو واحد على الأقل عشان نعرف مساحته."

# User did not select any video to download.
MSG_NO_VIDEO_DL = "اختار فيديو واحد على الأقل عشان نحمّله."

# User did not select any video to convert.
MSG_NO_VIDEO_CONV = "اختار فيديو واحد على الأقل عشان نحوله."

# Internet error or YouTube block.
MSG_BLOCKED = "الإنترنت فيه مشكلة أو يوتيوب قفش علينا شوية عشان بعتنا طلبات كتير ورا بعض.\n\nروح اشرب لك خربوش شاي وجرب تاني كمان شوية.\nولو مستعجل قوي، شغل VPN واعمل نفسك من بنها."

# User did not put a link.
MSG_URL_MISSING = "نسيت تحط رابط يوتيوب!\nحط الرابط وجرب تاني."

# YouTube does not answer.
MSG_CONN_ERROR = "يوتيوب مش راضي يرد علينا!\nيا إما النت عندك بعافية شوية، أو الرابط ده فيه مشكلة."

# User did not choose a save folder.
MSG_INVALID_PATH = "اختار المكان اللي هنحفظ فيه الفيديوهات الأول!\nمن المربع اللي فوق على الشمال اضغط على (Browse)."

# Ask about conversion speed.
MSG_SPEED_PROMPT = "تحب ننجز ونحول في السريع، ولا ناخد وقتنا على الهادي؟"

# Tell user they must download first before convert.
MSG_DL_REQUIRED = "الفيديوهات اللي انت اخترتها لسه متحملتش أصلًا.\nتحب أحملهالك الأول وبعدين أحوّلهالك؟"

# Ask to delete old files after convert.
MSG_CLEANUP = "التحويل خلص الحمدلله!\nأمسح لك بقى الملفات القديمة عشان منزحمش الجهاز على الفاضي؟"

# Ask to keep download and stop convert.
MSG_KEEP_DL_CANCEL_CONV = "في تحميل شغال دلوقتي.\nتحب نكمّل التحميل ونلغي التحويل؟"

# A job is already running.
MSG_OPERATION_RUNNING = "⏳ في عملية شغالة دلوقتي، استنى شوية "

# ------------------------------------------
# 5. Welcome Screen (Onboarding)
# ------------------------------------------
TITLE_WELCOME = "مرحبًا"
MSG_WELCOME_ASK = "أهلاً بيك يا صديقي، ممكن نتعرف؟"
MSG_WELCOME_GREET = "أهلاً وسهلاً بيك يا {name} نتمنى لك تجربة ممتعة 🎉"
BTN_CONFIRM_NAME = "يلا نبدأ"
PLACEHOLDER_NAME = "اكتب اسمك هنا... (o_o)"
MSG_NAME_REQUIRED = "ممكن تقولنا اسمك الأول؟"
MSG_INVALID_NAME = "ممكن تقولنا اسمك الحقيقي (^_^)\nالأرقام والرموز مش مدعوين هنا "
WELCOME_BTN = "يلا بينا.."

# ------------------------------------------
# 6. Exit Screen (Closing the app)
# ------------------------------------------
TITLE_EXIT = "هتمشي وتسيبني؟"
MSG_EXIT_ASK = "خلاص عايز تسيبني وتمشي؟"
BTN_STAY = "مقدرش أستغنى عنك"
BTN_LEAVE = "معلش، لازم أمشي"

# Exit warning (jobs are running).
TITLE_EXIT_WARN = "خد بالك!! ⚠️"
MSG_EXIT_WARN = "أنت بتحمل او بتحول ملفات دلوقتي! متأكد إنك عايز تقفل وتلغي العملية؟"
BTN_FORCE_QUIT = "ايوه اقفل"
BTN_WAIT = "لا استنى"

# ------------------------------------------
# 7. Contact Us Screen (Social Links)
# ------------------------------------------
BTN_CONTACT_US = "Contact Us"
FONT_SIZE_CONTACT_US = 14
FONT_FAMILY_CONTACT_US = "Segoe UI"
MSG_CONTACT_WHERE = "تحب نكمل كلامنا فين؟ "

URL_LINKEDIN = "https://www.linkedin.com/in/a-elmarakby/"
URL_WHATSAPP = "https://wa.me/201010043281"
URL_GITHUB = "https://github.com/A-Elmarakby"
URL_EMAIL = "mailto:abderhmanelmarakby20@gmail.com"

# ------------------------------------------
# 8. Fetching & Status Messages
# ------------------------------------------
STATUS_CONNECTING = "Connecting to YouTube... Please wait."
STATUS_LOADING = "Loading..."
STATUS_SEARCH_FAILED = "Search Failed."
UNKNOWN_TITLE = "Unknown Title"

# ------------------------------------------
# 9. Conversion Status Messages
# ------------------------------------------
STATUS_CONVERTING_REMUX = "Converting (Remuxing)..."
STATUS_CONVERTING_RECODE = "Converting (Re-encoding)..."
STATUS_ALREADY_MP4 = "Already MP4"
STATUS_AUDIO_FILE = "Audio File"