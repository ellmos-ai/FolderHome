# Synthetisches Artefaktstudio

[English](./README.md) | **Deutsch**

Die beiden Anfragen sind vollständig synthetisch. `artifact-request.json`
zeigt die gewünschte Office-, Design- und Medienbreite. Der Plan ruft keinen
Provider auf und weist fehlende Laufzeit- oder Sichtprüfungen ausdrücklich
aus.

`design-request.json` erzeugt nach Freigabe drei neue lokale Dateien:

- maschinenlesbare JSON-Designtokens
- wiederverwendbare CSS-Variablen
- eine SVG-Visitenkartenvorschau im Format 1050 × 600

Die Farbkombinationen müssen für normalen Text mindestens ein
WCAG-Kontrastverhältnis von 4,5:1 erfüllen. Eine erfolgreiche SVG-Erzeugung
ist noch keine visuelle Druckfreigabe.

---
<!-- REMEMBER: ENDUSERTEXTE BEKOMMEN ECHTE UMLAUTE Ü Ö Ä -->
