"""
Modelli delle email: layout HTML curato e riutilizzabile + testi.

Ogni funzione ritorna una coppia (testo_semplice, html). Il testo semplice e'
la ricaduta per i client che non mostrano l'HTML; l'html e' la versione ricca.
"""

# Colori CoordSync (coerenti col frontend)
_ACCIAIO = "#1e2a38"
_AMBRA = "#e6a817"


def _layout(titolo: str, righe_html: str, cta_testo: str = None, cta_link: str = None) -> str:
    """Impagina un'email in HTML: intestazione, corpo e (opzionale) pulsante."""
    bottone = ""
    if cta_testo and cta_link:
        bottone = f"""
        <tr><td style="padding: 8px 0 24px;">
          <a href="{cta_link}" style="display:inline-block; background:{_ACCIAIO};
             color:#ffffff; text-decoration:none; padding:12px 24px; border-radius:6px;
             font-weight:600; font-size:15px;">{cta_testo}</a>
        </td></tr>"""

    return f"""\
<!doctype html>
<html lang="it"><body style="margin:0; background:#eef1f4; font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#eef1f4; padding:24px 0;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#ffffff; border-radius:8px; overflow:hidden;
                    border-top:4px solid {_AMBRA};">
        <tr><td style="padding:24px 32px 8px;">
          <div style="font-size:22px; font-weight:700; color:{_ACCIAIO}; letter-spacing:0.02em;">
            CoordSync
          </div>
        </td></tr>
        <tr><td style="padding:8px 32px;">
          <h1 style="font-size:18px; color:{_ACCIAIO}; margin:0 0 12px;">{titolo}</h1>
          <table cellpadding="0" cellspacing="0"><tbody>
            {righe_html}
            {bottone}
          </tbody></table>
        </td></tr>
        <tr><td style="padding:16px 32px 28px;">
          <hr style="border:none; border-top:1px solid #e0e5ea; margin:0 0 12px;">
          <p style="font-size:12px; color:#8a94a0; margin:0;">
            CoordSync &middot; Coordinamento lavori per squadre tecniche<br>
            Se non hai richiesto tu questa email, puoi ignorarla in sicurezza.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def _riga(testo: str) -> str:
    return f'<tr><td style="font-size:15px; color:#3a4653; line-height:1.6; padding:4px 0;">{testo}</td></tr>'


def verifica_email(nome: str, link: str):
    oggetto = "Conferma il tuo indirizzo email"
    testo = (
        f"Ciao {nome},\n\n"
        "grazie per aver iniziato a usare CoordSync. Per completare la registrazione, "
        "conferma il tuo indirizzo email aprendo questo link:\n\n"
        f"{link}\n\n"
        "Il link scade tra 24 ore.\n\n"
        "Se non sei stato tu, ignora pure questa email.\n\n"
        "Il team di CoordSync"
    )
    html = _layout(
        titolo=f"Ciao {nome}, conferma la tua email",
        righe_html=(
            _riga("Grazie per aver iniziato a usare CoordSync.") +
            _riga("Per completare la registrazione, conferma il tuo indirizzo email:")
        ),
        cta_testo="Conferma email",
        cta_link=link,
    ) 
    # aggiungo una nota sotto il pulsante
    html = html.replace(
        "</tbody></table>",
        _riga('<span style="font-size:13px; color:#8a94a0;">Il link scade tra 24 ore.</span>') +
        "</tbody></table>",
        1,
    )
    return oggetto, testo, html


def invito(nome: str, azienda: str, link: str):
    oggetto = f"Invito a unirti a {azienda} su CoordSync"
    testo = (
        f"Ciao {nome},\n\n"
        f"sei stato invitato a unirti a {azienda} su CoordSync, la piattaforma "
        "di coordinamento lavori per squadre tecniche. Per attivare il tuo account, "
        "scegli la tua password aprendo questo link:\n\n"
        f"{link}\n\n"
        "Il link scade tra 7 giorni.\n\n"
        "Se non ti aspettavi questo invito, ignora pure questa email.\n\n"
        "Il team di CoordSync"
    )
    html = _layout(
        titolo=f"Ciao {nome}, ti aspettiamo su CoordSync",
        righe_html=(
            _riga(f"Sei stato invitato a unirti a <strong>{azienda}</strong> su CoordSync.") +
            _riga("Per attivare il tuo account, scegli la tua password:")
        ),
        cta_testo="Accetta l'invito",
        cta_link=link,
    )
    html = html.replace(
        "</tbody></table>",
        _riga('<span style="font-size:13px; color:#8a94a0;">Il link scade tra 7 giorni.</span>') +
        "</tbody></table>",
        1,
    )
    return oggetto, testo, html


def reset_password(nome: str, link: str):
    oggetto = "Reimposta la tua password"
    testo = (
        f"Ciao {nome},\n\n"
        "abbiamo ricevuto una richiesta di reimpostazione della password del tuo account CoordSync. "
        "Scegli una nuova password aprendo questo link:\n\n"
        f"{link}\n\n"
        "Il link scade tra 1 ora. Se non hai richiesto tu il reset, ignora questa email: "
        "la tua password resta invariata.\n\n"
        "Il team di CoordSync"
    )
    html = _layout(
        titolo=f"Ciao {nome}, reimposta la password",
        righe_html=(
            _riga("Abbiamo ricevuto una richiesta di reimpostazione della password del tuo account.") +
            _riga("Scegli una nuova password cliccando qui sotto:")
        ),
        cta_testo="Reimposta password",
        cta_link=link,
    )
    html = html.replace(
        "</tbody></table>",
        _riga('<span style="font-size:13px; color:#8a94a0;">Il link scade tra 1 ora. '
              'Se non hai richiesto tu il reset, la password resta invariata.</span>') +
        "</tbody></table>",
        1,
    )
    return oggetto, testo, html


def promemoria_impegno(nome: str, titolo: str, quando: str, luogo: str | None,
                       fra_quanto: str, link: str):
    """Il promemoria di un impegno in agenda, mandato poco prima che arrivi."""
    oggetto = f"Promemoria: {titolo} - {quando}"

    parti = [
        f"Ciao {nome},",
        "",
        f"ti ricordo che fra {fra_quanto} hai in agenda:",
        "",
        titolo,
        f"Quando: {quando}",
    ]
    if luogo:
        parti.append(f"Dove: {luogo}")
    parti += ["", "Puoi vedere l'agenda completa qui:", link, "", "Il team di CoordSync"]
    testo = "\n".join(parti)

    righe = _riga(f"Ti ricordo che <strong>fra {fra_quanto}</strong> hai in agenda:")
    righe += _riga(f'<span style="font-size:17px; color:{_ACCIAIO};"><strong>{titolo}</strong></span>')
    righe += _riga(f"Quando: {quando}")
    if luogo:
        righe += _riga(f"Dove: {luogo}")

    html = _layout(titolo=f"Ciao {nome}, un promemoria", righe_html=righe,
                   cta_testo="Apri l'agenda", cta_link=link)
    return oggetto, testo, html
