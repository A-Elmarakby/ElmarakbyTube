import customtkinter as ctk

app = ctk.CTk()
app.geometry("800x700")
app.title("Tkinter Emoji & Bidi Lab")
ctk.set_appearance_mode("Dark")

# دالة Bidi الخاصة بيك عشان نثبت المتغيرات
def apply_bidi(text):
    text = str(text)
    if any('\u0600' <= c <= '\u06FF' for c in text):
        lines = text.split('\n')
        # التغليف القوي لمنع هروب علامات الترقيم
        return '\n'.join(['\u202B\u200F' + line + '\u200F\u202C' for line in lines])
    return text

scroll = ctk.CTkScrollableFrame(app)
scroll.pack(fill="both", expand=True, padx=20, pady=20)

font_main = ("Segoe UI", 18, "bold")

# دالة لرسم الاختبارات العادية (دمج النصوص)
def add_test_row(desc, result_text):
    frame = ctk.CTkFrame(scroll, fg_color="#333", height=50)
    frame.pack(fill="x", pady=5)
    
    ctk.CTkLabel(frame, text=desc, width=350, anchor="w", text_color="cyan").pack(side="left", padx=10)
    ctk.CTkLabel(frame, text=result_text, font=font_main).pack(side="right", padx=10)

# دالة لرسم الحل المعماري (فصل الإيموجي والنص في فريم)
def add_frame_test(desc, title, icon):
    frame = ctk.CTkFrame(scroll, fg_color="#183B19", height=50)
    frame.pack(fill="x", pady=5)
    
    ctk.CTkLabel(frame, text=desc, width=350, anchor="w", text_color="yellow").pack(side="left", padx=10)
    
    # الفريم اللي هيحتويهم
    container = ctk.CTkFrame(frame, fg_color="transparent")
    container.pack(side="right", padx=10)
    
    # بما إننا بنرص من اليمين (pack side="right"):
    # أول عنصر بنرصه هو الإيموجي (عشان يلزق في أقصى اليمين)
    ctk.CTkLabel(container, text=f"{icon} ", font=font_main).pack(side="right")
    # وتاني عنصر هو النص العربي
    ctk.CTkLabel(container, text=apply_bidi(title), font=font_main).pack(side="right")

# ================= الحالات اللي بنختبرها =================

title_err = "خطأ"
icon_err = "🛑"

title_warn = "خد بالك!!"
icon_warn = "⚠️"

# 1. اختبارات الخطأ (بدون علامات ترقيم)
ctk.CTkLabel(scroll, text="=== اختبارات الخطأ 🛑 (بدون علامات ترقيم) ===", font=("Arial", 16, "bold")).pack(pady=(20, 5))
add_test_row("1. f'{icon} {apply_bidi(title)}'", f"{icon_err} {apply_bidi(title_err)}")
add_test_row("2. f'{apply_bidi(title)} {icon}'", f"{apply_bidi(title_err)} {icon_err}")
add_test_row("3. apply_bidi(f'{icon} {title}')", apply_bidi(f"{icon_err} {title_err}"))
add_test_row("4. apply_bidi(f'{title} {icon}')", apply_bidi(f"{title_err} {icon_err}"))

# 2. اختبارات التحذير (مع علامات ترقيم !!)
ctk.CTkLabel(scroll, text="=== اختبارات التحذير ⚠️ (مع علامات ترقيم !!) ===", font=("Arial", 16, "bold")).pack(pady=(20, 5))
add_test_row("5. f'{icon} {apply_bidi(title)}'", f"{icon_warn} {apply_bidi(title_warn)}")
add_test_row("6. f'{apply_bidi(title)} {icon}'", f"{apply_bidi(title_warn)} {icon_warn}")
add_test_row("7. apply_bidi(f'{icon} {title}')", apply_bidi(f"{icon_warn} {title_warn}"))
add_test_row("8. apply_bidi(f'{title} {icon}')", apply_bidi(f"{title_warn} {icon_warn}"))

# 3. الحل المعماري (الفصل التام)
ctk.CTkLabel(scroll, text="=== الحل المعماري (فصل الإيموجي في Label مستقل) ===", font=("Arial", 16, "bold"), text_color="yellow").pack(pady=(20, 5))
add_frame_test("9. Frame Separation (Error 🛑)", title_err, icon_err)
add_frame_test("10. Frame Separation (Warning ⚠️)", title_warn, icon_warn)

app.mainloop()