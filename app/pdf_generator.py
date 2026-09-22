import io
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def _qr_image(data: str):
    img = qrcode.make(data)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def generate_vouchers_pdf(batch, vouchers) -> bytes:
    buffer = io.BytesIO()
    page_width, page_height = A4
    c = canvas.Canvas(buffer, pagesize=A4)

    ticket_width = 60 * mm
    ticket_height = 35 * mm
    margin = 10 * mm
    cols = int((page_width - 2 * margin) // ticket_width)
    rows = int((page_height - 2 * margin) // ticket_height)
    per_page = max(cols * rows, 1)

    for index, voucher in enumerate(vouchers):
        position_on_page = index % per_page
        if position_on_page == 0 and index != 0:
            c.showPage()

        col = position_on_page % cols
        row = position_on_page // cols

        x = margin + col * ticket_width
        y = page_height - margin - (row + 1) * ticket_height

        c.rect(x, y, ticket_width, ticket_height)

        qr_size = 25 * mm
        qr_img = _qr_image(voucher.code)
        c.drawImage(qr_img, x + 3 * mm, y + 5 * mm, width=qr_size, height=qr_size)

        text_x = x + qr_size + 6 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(text_x, y + ticket_height - 8 * mm, batch.profile_name)
        c.setFont("Helvetica", 9)
        c.drawString(text_x, y + ticket_height - 14 * mm, f"Code: {voucher.code}")
        c.drawString(text_x, y + ticket_height - 20 * mm, f"{batch.prix_unitaire:.0f} FCFA")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def generate_router_setup_card(router, video_url: str) -> bytes:
    buffer = io.BytesIO()
    page_width, page_height = A4
    c = canvas.Canvas(buffer, pagesize=A4)

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(page_width / 2, page_height - 40 * mm, "Fiche d'installation MIABEWIFI")

    c.setFont("Helvetica", 13)
    c.drawCentredString(page_width / 2, page_height - 55 * mm, f"Routeur : {router.nom}")

    if video_url:
        qr_size = 60 * mm
        qr_img = _qr_image(video_url)
        c.drawImage(
            qr_img,
            (page_width - qr_size) / 2,
            page_height - 130 * mm,
            width=qr_size,
            height=qr_size,
        )
        c.setFont("Helvetica", 11)
        c.drawCentredString(
            page_width / 2,
            page_height - 140 * mm,
            "Scannez ce code pour voir le tutoriel vidéo",
        )

    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(
        page_width / 2,
        30 * mm,
        "Gardez cette fiche près de votre routeur.",
    )

    c.save()
    buffer.seek(0)
    return buffer.getvalue()