# Clip Studio

Eigen AI-clipping tool: gooi er een YouTube-link of videobestand in (max 60 min),
en de AI knipt er meerdere "viral"-clips uit met ingebrande ondertiteling,
klaar voor TikTok/Reels/Shorts.

Werkt volledig als één programma: de website (`static/`) én de AI-verwerking
(`app/`) draaien samen op Render.

## Wat je nodig hebt

- Een gratis [Groq](https://console.groq.com/keys) API-key (voor transcriptie + gratis clipselectie-AI)
- Optioneel: een [Anthropic](https://console.anthropic.com/settings/keys) API-key als je liever Claude gebruikt voor het kiezen van de beste momenten
- Een GitHub-account
- Een Render-account ([render.com](https://render.com), inloggen kan met je GitHub-account)

## Stap 1 — Code naar GitHub

1. Ga naar [github.com/new](https://github.com/new) en maak een nieuwe (private mag) repository, bv. `clip-studio`.
2. Upload alle bestanden uit deze map naar die repository (via "Add file" → "Upload files" in de GitHub-webinterface, zoals je gewend bent).
3. Zorg dat de mapstructuur behouden blijft: `app/`, `static/`, `Dockerfile`, `requirements.txt` moeten allemaal in de hoofdmap van de repository staan.

## Stap 2 — Render-service aanmaken

1. Log in op [render.com](https://render.com) en klik op **New +** → **Web Service**.
2. Koppel je GitHub-account en kies de `clip-studio` repository.
3. Render herkent automatisch de `Dockerfile` — laat "Environment" op **Docker** staan.
4. Kies een **plan**: het gratis plan (Free) werkt voor korte testjes, maar loopt vast bij een uur-lange video (te weinig geheugen, en de service "slaapt" na inactiviteit). Voor echt gebruik: kies minstens het **Starter**-plan (~$7/maand).
5. Klik op **Create Web Service**.

## Stap 3 — API-keys instellen

In je Render-service, ga naar **Environment** en voeg toe:

| Key | Value |
|---|---|
| `GROQ_API_KEY` | jouw Groq-sleutel |
| `ANTHROPIC_API_KEY` | (optioneel) jouw Anthropic-sleutel |

Render herstart de service automatisch zodra je een environment variable opslaat.

## Stap 4 — Klaar

Na de eerste build (kan 3-5 minuten duren omdat ffmpeg geïnstalleerd wordt)
krijg je een URL zoals `https://clip-studio-xxxx.onrender.com`. Open die —
dat is je eigen ClipParty-achtige tool.

## Bekende beperkingen van deze eerste versie

- Er is geen automatische gezichtsdetectie voor het bijsnijden naar 9:16 —
  de tool snijdt nu simpelweg het midden van het beeld uit. Werkt prima voor
  podcasts/interviews met de spreker centraal in beeld, minder goed als
  belangrijke actie aan de zijkant gebeurt.
- Video's worden tijdelijk op de Render-server opgeslagen. Bij een herstart
  van de service (bv. na een nieuwe deploy) gaan oude clips verloren — download
  ze dus op tijd.
- Alleen getest tot ongeveer 60 minuten bronmateriaal, zoals gevraagd.

Wil je hier later gezichts-tracking, langere opslag, of iets anders aan
toevoegen — dat kan, dat bouwen we dan als volgende stap.
