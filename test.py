import customtkinter as ctk
import arabic_reshaper
from bidi.algorithm import get_display

app = ctk.CTk()
app.title("اختبار النصوص العربية")
app.geometry("500x400")

# جملة الاختبار فيها عربي + إنجليزي + علامات ترقيم عشان نحاكي المشكلة بالظبط
test_text = "أهلاً بيك يا Ahmed في التطبيق، جاهز؟"

# الطريقة الأولى: النص الخام (بدون أي تعديل)
ctk.CTkLabel(app, text=f"1. Raw:\n{test_text}", font=("Arial", 16, "bold"), text_color="cyan").pack(pady=10)

# الطريقة الثانية: تشبيك الحروف فقط (Reshape Only)
reshaped = arabic_reshaper.reshape(test_text)
ctk.CTkLabel(app, text=f"2. Reshape Only:\n{reshaped}", font=("Arial", 16, "bold"), text_color="yellow").pack(pady=10)

# الطريقة الثالثة: تشبيك الحروف + قلب الكلمات (Reshape + BiDi)
bidi_text = get_display(reshaped)
ctk.CTkLabel(app, text=f"3. Reshape + BiDi:\n{bidi_text}", font=("Arial", 16, "bold"), text_color="lightgreen").pack(pady=10)

# الطريقة الرابعة: شفرة اليونيكود للإجبار على اليمين لليسار (Unicode RTL)
unicode_text = '\u202B' + test_text + '\u202C'
ctk.CTkLabel(app, text=f"4. Unicode RTL:\n{unicode_text}", font=("Arial", 16, "bold"), text_color="orange").pack(pady=10)

app.mainloop()