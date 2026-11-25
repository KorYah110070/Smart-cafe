"""
โครงของ RAG pipeline (FR-15, FR-16, FR-17) ตามไดอะแกรม AI RAG Workflow ในสไลด์
ตอนนี้ยังเป็น 'Retrieval' แบบ keyword search ธรรมดา (ยังไม่เชื่อม LLM จริง)
เมื่อพร้อมเชื่อม LLM ให้แทนที่ฟังก์ชัน generate_answer() ด้วยการเรียก API จริง
(เช่น OpenAI / Gemini) โดยส่ง context ที่ retrieve() คืนมาเป็น prompt
"""

from django.db.models import Q

from .models import KnowledgeSnippet


def retrieve(question: str, top_k: int = 5):
    """Retrieval stage: ค้นหาข้อมูลที่เกี่ยวข้องจาก Knowledge Base แบบ keyword matching เบื้องต้น"""
    keywords = [w for w in question.split() if len(w) > 1]
    query = Q()
    for kw in keywords:
        query |= Q(content__icontains=kw)

    if not query:
        return list(KnowledgeSnippet.objects.all()[:top_k])

    return list(KnowledgeSnippet.objects.filter(query)[:top_k])


def augment(question: str, snippets) -> str:
    """Augmentation stage: รวมคำถามลูกค้า + ข้อมูลที่ค้นพบ เป็น context เดียว"""
    context_lines = "\n".join(f"- {s.content}" for s in snippets)
    return f"คำถามของลูกค้า: {question}\n\nข้อมูลที่เกี่ยวข้องจากร้าน:\n{context_lines}"


def generate_answer(question: str) -> str:
    """
    Generation stage (stub): ตอนนี้ยังไม่เชื่อม LLM จริง
    ให้คืนค่าข้อมูลที่ค้นเจอแบบตรงไปตรงมาไปก่อน เพื่อให้ทดสอบ flow ได้ครบวงจร
    """
    snippets = retrieve(question)
    if not snippets:
        return "ขออภัยค่ะ ยังไม่มีข้อมูลที่เกี่ยวข้องในระบบสำหรับคำถามนี้"

    context = augment(question, snippets)
    return (
        "(นี่คือคำตอบชั่วคราวจาก Retrieval เท่านั้น ยังไม่ได้เชื่อม LLM จริง)\n\n" + context
    )


def personalized_recommendation(user=None) -> str:
    """
    FR-17: แนะนำเมนู/โปรโมชั่นแบบเฉพาะบุคคล สำหรับแผง "แนะนำเมนู โปรโมชั่นนี้" บนหน้าแดชบอร์ด

    ตอนนี้ Retrieval stage ดึงตรงจากตาราง Menu/Promotion จริง (แทนที่จะพึ่งพา KnowledgeSnippet
    ที่ต้องให้แอดมินกรอกเอง) ส่วน Generation stage ยังเป็น template ธรรมดา ยังไม่เชื่อม LLM จริง
    ตามสถาปัตยกรรม AI RAG Workflow เดิม ถ้าต้องการสุ่มแนะนำแบบรู้ใจลูกค้าจริง ๆ (เช่น จากประวัติ
    การสั่งซื้อ) ให้ต่อยอดจาก Order/OrderItem ของ user คนนั้นแทนการสุ่มแบบนี้

    user=None (ผู้เยี่ยมชมที่ยังไม่ล็อกอิน): แนะนำเมนู/โปรโมชั่นแบบทั่วไป (ยังไม่ผูกกับประวัติส่วนตัว)
    """
    from datetime import date

    from menus.models import MenuItem
    from promotions.models import Promotion

    today = date.today()
    promo = Promotion.objects.filter(
        is_active=True, start_date__lte=today, end_date__gte=today
    ).first()
    menu_item = MenuItem.objects.filter(is_available=True).order_by("?").first()

    if not menu_item and not promo:
        return "ยังไม่มีข้อมูลเมนูหรือโปรโมชั่นในระบบตอนนี้ค่ะ (แอดมินยังไม่ได้เพิ่มข้อมูล)"

    greeting = f"สวัสดีค่ะคุณ {user.username} วันนี้แนะนำ:" if (user and user.is_authenticated) else "วันนี้แนะนำ:"
    lines = [greeting]
    if menu_item:
        lines.append(f"- {menu_item.name} ราคา {menu_item.price} บาท")
    if promo:
        lines.append(f'- โปรโมชั่น "{promo.title}" ลด {promo.discount_percent}%')
    lines.append("พิมพ์คุยกับแชทบอทด้านล่างได้เลยถ้าอยากถามเพิ่มเติมนะคะ")
    return "\n".join(lines)
