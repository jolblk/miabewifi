import io
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor


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


# ---------------------------------------------------------------------------
# Fiche d'installation MIABEWIFI : guide complet, page par page, en langage
# simple. Les fonctions ci-dessous sont de petits outils réutilisés par
# generate_router_setup_card pour ne pas répéter le code de mise en page.
# ---------------------------------------------------------------------------

_PAGE_MARGIN = 20 * mm
_ACCENT_COLOR = HexColor("#7c3aed")  # violet MIABEWIFI


def _wrap_text(c, text: str, font: str, size: int, max_width: float) -> list[str]:
    """Découpe `text` en lignes qui tiennent dans max_width, pour cette police/taille."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if c.stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _page_header(c, page_width, page_height, title: str, step_label: str | None = None):
    """En-tête commun à chaque page : bande de couleur + titre + repère d'étape."""
    c.setFillColor(_ACCENT_COLOR)
    c.rect(0, page_height - 22 * mm, page_width, 22 * mm, fill=1, stroke=0)

    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(_PAGE_MARGIN, page_height - 14 * mm, title)

    if step_label:
        c.setFont("Helvetica", 10)
        c.drawRightString(page_width - _PAGE_MARGIN, page_height - 14 * mm, step_label)

    c.setFillColor(HexColor("#000000"))


def _page_footer(c, page_width, page_number: int, total_pages: int):
    c.setFillColor(HexColor("#888888"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(page_width / 2, 12 * mm, f"MIABEWIFI — Guide d'installation — Page {page_number}/{total_pages}")
    c.setFillColor(HexColor("#000000"))


def _draw_intro(c, page_width, page_height, y_start: float, text: str) -> float:
    """Paragraphe d'introduction en haut d'une page. Retourne le y après le texte."""
    c.setFont("Helvetica", 11)
    max_width = page_width - 2 * _PAGE_MARGIN
    y = y_start
    for line in _wrap_text(c, text, "Helvetica", 11, max_width):
        c.drawString(_PAGE_MARGIN, y, line)
        y -= 6 * mm
    return y - 4 * mm


def _draw_bullets(c, page_width, y_start: float, items: list[str], bold_prefix: bool = False) -> float:
    """Liste à puces avec retour à la ligne automatique. Retourne le y final."""
    max_width = page_width - 2 * _PAGE_MARGIN - 8 * mm
    y = y_start
    for item in items:
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(_ACCENT_COLOR)
        c.drawString(_PAGE_MARGIN, y, "•")
        c.setFillColor(HexColor("#000000"))
        c.setFont("Helvetica", 11)
        lines = _wrap_text(c, item, "Helvetica", 11, max_width)
        for i, line in enumerate(lines):
            c.drawString(_PAGE_MARGIN + 8 * mm, y, line)
            y -= 6 * mm
        y -= 2 * mm
    return y


def _draw_warning(c, page_width, y_start: float, text: str) -> float:
    """Encadré d'avertissement (fond clair, texte en gras)."""
    max_width = page_width - 2 * _PAGE_MARGIN - 10 * mm
    lines = _wrap_text(c, text, "Helvetica-Bold", 10, max_width)
    box_height = len(lines) * 5.5 * mm + 6 * mm
    box_top = y_start
    box_bottom = box_top - box_height

    c.setFillColor(HexColor("#fdf0e6"))
    c.rect(_PAGE_MARGIN, box_bottom, page_width - 2 * _PAGE_MARGIN, box_height, fill=1, stroke=0)

    c.setFillColor(HexColor("#9a4b00"))
    c.setFont("Helvetica-Bold", 10)
    y = box_top - 8 * mm
    for line in lines:
        c.drawString(_PAGE_MARGIN + 5 * mm, y, line)
        y -= 5.5 * mm

    c.setFillColor(HexColor("#000000"))
    return box_bottom - 6 * mm


def generate_router_setup_card(router, video_url: str) -> bytes:
    """Guide d'installation complet MIABEWIFI : du matériel nécessaire jusqu'à
    un routeur connecté et prêt à l'emploi, en langage grand public."""
    buffer = io.BytesIO()
    page_width, page_height = A4
    c = canvas.Canvas(buffer, pagesize=A4)
    total_pages = 6

    # --- Page 1 : couverture + matériel nécessaire ---
    c.setFillColor(_ACCENT_COLOR)
    c.rect(0, 0, page_width, page_height, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(page_width / 2, page_height - 60 * mm, "Guide d'installation")
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(page_width / 2, page_height - 72 * mm, "MIABEWIFI")
    c.setFont("Helvetica", 13)
    c.drawCentredString(page_width / 2, page_height - 85 * mm, f"Routeur : {router.nom}")
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(page_width / 2, 25 * mm, "Gardez cette fiche près de votre routeur.")
    c.showPage()

    # --- Page 2 : ce dont vous avez besoin ---
    _page_header(c, page_width, page_height, "Avant de commencer", "Ce qu'il vous faut")
    y = _draw_intro(
        c, page_width, page_height, page_height - 35 * mm,
        "Rassemblez ces quelques éléments avant de démarrer. L'installation prend "
        "environ 15 minutes et ne se fait qu'une seule fois par routeur.",
    )
    y = _draw_bullets(c, page_width, y, [
        "Un routeur MikroTik, n'importe quel modèle, avec le logiciel RouterOS "
        "en version 7 ou plus récente (on vérifie ça à l'étape suivante).",
        "Une connexion Internet déjà branchée et active sur ce routeur.",
        "Un ordinateur (Windows, Mac ou Linux) pour faire la configuration une "
        "seule fois. Le routeur n'a pas besoin d'être connecté à cet "
        "ordinateur en permanence après.",
        "Le logiciel gratuit \"Winbox\", à télécharger sur mikrotik.com/download "
        "(quelques Mo, aucune installation compliquée).",
        "Un smartphone, pour scanner les codes de cette fiche si besoin.",
    ])
    _page_footer(c, page_width, 2, total_pages)
    c.showPage()

    # --- Page 3 : vérifier / mettre à jour RouterOS ---
    _page_header(c, page_width, page_height, "Vérifier votre routeur", "Étape 1 sur 4")
    y = _draw_intro(
        c, page_width, page_height, page_height - 35 * mm,
        "Ouvrez Winbox et connectez-vous à votre routeur comme d'habitude "
        "(onglet Neighbors, cliquez sur votre routeur, puis Connect).",
    )
    y = _draw_bullets(c, page_width, y, [
        "En haut à droite de la fenêtre Winbox, une ligne indique la version "
        "de RouterOS installée.",
        "Si elle commence par \"7.\" : parfait, passez directement à la page suivante.",
        "Si elle commence par \"6.\" ou un chiffre plus petit : une mise à jour "
        "est nécessaire, suivez les 3 points ci-dessous.",
    ])
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(_PAGE_MARGIN, y, "Pour mettre à jour :")
    y -= 8 * mm
    y = _draw_bullets(c, page_width, y, [
        "Dans Winbox, menu \"System\" puis \"Packages\", cliquez sur "
        "\"Check For Updates\".",
        "Choisissez le canal \"stable\" puis cliquez sur \"Download & Upgrade\".",
        "Le routeur redémarre seul après quelques minutes : ne coupez surtout "
        "pas son alimentation pendant ce temps.",
    ])
    y = _draw_warning(
        c, page_width, y,
        "Ne débranchez jamais le routeur pendant une mise à jour, même si "
        "cela semble long. Une coupure à ce moment-là peut rendre le "
        "routeur inutilisable.",
    )
    _page_footer(c, page_width, 3, total_pages)
    c.showPage()

    # --- Page 4 : coller le script de configuration ---
    _page_header(c, page_width, page_height, "Configurer le routeur", "Étape 2 sur 4")
    y = _draw_intro(
        c, page_width, page_height, page_height - 35 * mm,
        "Retournez sur l'application MIABEWIFI, à l'écran où un script vous a "
        "été donné, et copiez-le entièrement.",
    )
    y = _draw_bullets(c, page_width, y, [
        "Dans Winbox, ouvrez le menu \"New Terminal\".",
        "Cliquez dans la zone noire, puis collez le script (clic droit, "
        "\"Paste\", ou le raccourci Ctrl+V).",
        "Appuyez sur la touche Entrée pour valider.",
        "Retournez sur l'application MIABEWIFI : elle détecte automatiquement "
        "la connexion en quelques secondes, vous n'avez rien d'autre à faire.",
    ])
    _page_footer(c, page_width, 4, total_pages)
    c.showPage()

    # --- Page 5 : autoriser l'application à gérer le routeur ---
    _page_header(c, page_width, page_height, "Autoriser MIABEWIFI", "Étape 3 sur 4")
    y = _draw_intro(
        c, page_width, page_height, page_height - 35 * mm,
        "Une dernière chose à activer sur le routeur pour que l'application "
        "puisse créer et gérer vos accès Wi-Fi.",
    )
    y = _draw_bullets(c, page_width, y, [
        "Dans Winbox, menu \"IP\" puis \"Services\".",
        "Repérez la ligne \"www-ssl\" et double-cliquez dessus.",
        "Décochez la case \"Disabled\" si elle est cochée, puis validez avec OK "
        "(si aucun certificat n'est proposé, laissez Winbox en créer un "
        "automatiquement).",
        "Sur l'application MIABEWIFI, dans les réglages de votre routeur, "
        "saisissez un nom d'utilisateur et un mot de passe : ceux que vous "
        "utilisez déjà pour vous connecter au routeur, ou un utilisateur "
        "dédié créé via \"System\" puis \"Users\" dans Winbox.",
    ])
    _page_footer(c, page_width, 5, total_pages)
    c.showPage()

    # --- Page 6 : vidéo + support ---
    _page_header(c, page_width, page_height, "Besoin d'un coup de main ?", "Étape 4 sur 4")
    y = _draw_intro(
        c, page_width, page_height, page_height - 35 * mm,
        "Votre routeur est maintenant connecté et prêt. Si un point n'est pas "
        "clair, ces deux ressources sont là pour vous.",
    )
    if video_url:
        qr_size = 45 * mm
        qr_img = _qr_image(video_url)
        c.drawImage(qr_img, (page_width - qr_size) / 2, y - qr_size, width=qr_size, height=qr_size)
        c.setFont("Helvetica", 11)
        c.drawCentredString(page_width / 2, y - qr_size - 8 * mm, "Scannez ce code pour voir le tutoriel vidéo")
        y = y - qr_size - 20 * mm
    c.setFont("Helvetica", 11)
    c.drawCentredString(
        page_width / 2, y,
        "Bloqué à une étape ? Utilisez le bouton \"Besoin d'aide ?\" dans "
        "l'application, notre équipe vous recontacte rapidement.",
    )
    _page_footer(c, page_width, 6, total_pages)
    c.showPage()

    c.save()
    buffer.seek(0)
    return buffer.getvalue()