import io
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor

from app.branding import DEFAULT_BRAND_COLOR, logo_bytes
from app.ros_utils import format_duration_fr, format_quota_fr, parse_ros_duration


def _qr_image(data: str):
    img = qrcode.make(data)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def _fit_font_size(c, text: str, font: str, size: float, max_width: float, min_size: float = 6) -> float:
    """Réduit la taille de police jusqu'à ce que `text` tienne dans max_width."""
    while size > min_size and c.stringWidth(text, font, size) > max_width:
        size -= 0.5
    return size


def generate_vouchers_pdf(
    batch, vouchers, wifi_ssid: str | None = None,
    brand_name: str | None = None, brand_color: str | None = None, brand_logo: str | None = None,
) -> bytes:
    """Planche de tickets à découper. Chaque ticket indique le code, le prix, la durée,
    le quota de données, la validité, le nom du Wi-Fi et comment se connecter.
    Avec un nom, une couleur ou un logo personnalisé, une bande en-tête est ajoutée."""
    buffer = io.BytesIO()
    page_width, page_height = A4
    c = canvas.Canvas(buffer, pagesize=A4)

    ticket_width = 62 * mm
    ticket_height = 42 * mm
    margin = 8 * mm
    pad = 2 * mm
    cols = int((page_width - 2 * margin) // ticket_width)
    rows = int((page_height - 2 * margin) // ticket_height)
    per_page = max(cols * rows, 1)

    duree = format_duration_fr(parse_ros_duration(batch.limit_uptime)) if batch.limit_uptime else None
    validite = f"Valable {batch.validite_jours} j après la 1re connexion" if batch.validite_jours else None
    quota = format_quota_fr(getattr(batch, "quota_mo", None))

    branded = bool(brand_name or brand_color or brand_logo)
    accent = HexColor(brand_color or DEFAULT_BRAND_COLOR)
    band_h = 5 * mm if branded else 0
    logo_png = logo_bytes(brand_logo)
    logo_reader = ImageReader(io.BytesIO(logo_png)) if logo_png else None

    for index, voucher in enumerate(vouchers):
        position_on_page = index % per_page
        if position_on_page == 0 and index != 0:
            c.showPage()

        col = position_on_page % cols
        row = position_on_page // cols

        x = margin + col * ticket_width
        y = page_height - margin - (row + 1) * ticket_height
        top = y + ticket_height

        c.setLineWidth(0.5)
        c.setStrokeColor(HexColor("#000000"))
        c.rect(x, y, ticket_width, ticket_height)

        if branded:
            c.setFillColor(accent)
            c.rect(x, top - band_h, ticket_width, band_h, fill=1, stroke=0)
            text_left = x + pad
            if logo_reader:
                c.setFillColor(HexColor("#ffffff"))
                c.rect(x + 0.6 * mm, top - band_h + 0.6 * mm, band_h - 1.2 * mm, band_h - 1.2 * mm, fill=1, stroke=0)
                c.drawImage(
                    logo_reader, x + 0.9 * mm, top - band_h + 0.9 * mm,
                    width=band_h - 1.8 * mm, height=band_h - 1.8 * mm,
                    preserveAspectRatio=True, mask="auto",
                )
                text_left = x + band_h + 1 * mm
            if brand_name:
                c.setFillColor(HexColor("#ffffff"))
                size = _fit_font_size(c, brand_name, "Helvetica-Bold", 8, ticket_width - (text_left - x) - pad, 5)
                c.setFont("Helvetica-Bold", size)
                c.drawString(text_left, top - band_h + 1.6 * mm, brand_name)
            c.setFillColor(HexColor("#000000"))
        top -= band_h  # tout le contenu du ticket se place sous la bande

        # QR code à gauche
        qr_size = 20 * mm
        c.drawImage(_qr_image(voucher.code), x + pad, top - pad - qr_size, width=qr_size, height=qr_size)

        # Colonne de droite : forfait, code, prix, durée, validité
        text_x = x + pad + qr_size + 3 * mm
        text_w = ticket_width - (text_x - x) - pad

        name_font = _fit_font_size(c, batch.profile_name, "Helvetica-Bold", 9, text_w)
        c.setFont("Helvetica-Bold", name_font)
        c.drawString(text_x, top - 6 * mm, batch.profile_name)

        code_font = _fit_font_size(c, voucher.code, "Courier-Bold", 13, text_w)
        c.setFont("Courier-Bold", code_font)
        c.drawString(text_x, top - 12 * mm, voucher.code)

        c.setFont("Helvetica-Bold", 10)
        c.drawString(text_x, top - 18 * mm, f"{batch.prix_unitaire:.0f} FCFA")

        if duree:
            c.setFont("Helvetica", 7)
            c.drawString(text_x, top - 21.5 * mm, f"{duree} de connexion")
        if quota:
            c.setFont("Helvetica", 7)
            c.drawString(text_x, top - 24.5 * mm, f"Quota : {quota}")

        # Bas du ticket : validité, Wi-Fi et comment se connecter
        full_w = ticket_width - 2 * pad
        bottom_y = top - 28 * mm
        if validite:
            c.setFont("Helvetica", _fit_font_size(c, validite, "Helvetica", 6.5, full_w, 5.5))
            c.drawString(x + pad, bottom_y, validite)
            bottom_y -= 3.2 * mm
        if wifi_ssid:
            wifi_line = f"Wi-Fi : {wifi_ssid}"
            c.setFont("Helvetica-Bold", _fit_font_size(c, wifi_line, "Helvetica-Bold", 7.5, full_w, 5.5))
            c.drawString(x + pad, bottom_y, wifi_line)
            bottom_y -= 3.2 * mm
        c.setFont("Helvetica", 6)
        howto = "1. Connectez-vous au Wi-Fi. 2. Ouvrez une page web. 3. Saisissez le code ci-dessus (dans Nom d'utilisateur ET Mot de passe si on vous demande les deux)."
        if branded:
            howto = "Saisissez ce code sur la page de connexion."
        ticket_bottom = top - (ticket_height - band_h)
        for line in _wrap_text(c, howto, "Helvetica", 6, full_w)[:3]:
            if bottom_y < ticket_bottom + 1.5 * mm:
                break  # jamais de texte hors du cadre
            c.drawString(x + pad, bottom_y, line)
            bottom_y -= 2.8 * mm

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
    _page_header(c, page_width, page_height, "Vérification automatique", "Étape 3 sur 4")
    y = _draw_intro(
        c, page_width, page_height, page_height - 35 * mm,
        "Il n'y a rien à faire sur cette page : MIABEWIFI s'occupe du reste.",
    )
    y = _draw_bullets(c, page_width, y, [
        "Le script de l'étape précédente a déjà autorisé l'application à "
        "gérer votre routeur : aucun réglage à saisir.",
        "Dès que le routeur est connecté, l'application vérifie sa version "
        "et prépare vos forfaits automatiquement.",
        "Si un message d'erreur s'affiche dans l'application, suivez-le ou "
        "utilisez le bouton \"Besoin d'aide ?\".",
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