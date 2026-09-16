pragma Singleton
import QtQuick

QtObject {
    property string mode: "midnight"
    // Midnight is intentionally cool and near-black: it lets the colours of
    // lights be the visual accent instead of competing with the workspace.
    property color bg: "#070a14"
    property color surface: "#0d1427"
    property color card: "#121c33"
    property color cardHi: "#182542"
    property color stroke: "#293958"
    property color primary: "#6697ff"
    property color primaryDark: "#4978ec"
    property color accent: "#b392ff"
    property color success: "#34d399"
    property color warning: "#fbbf24"
    property color error: "#f87171"
    property color text: "#f4f7ff"
    property color muted: "#a4b0ca"
    property color faint: "#697899"
    readonly property color highlight: "#ffffff"
    readonly property color shadow: "#02040b"
    readonly property int radiusSmall: 10
    readonly property int radiusMedium: 16
    readonly property int radiusLarge: 22
    // Shared motion preference.  Pages and controls consume these tokens so
    // the accessibility setting behaves consistently across the shell.
    property bool reduceMotion: false
    property int motionFast: reduceMotion ? 0 : 220
    property int motionNormal: reduceMotion ? 0 : 360
    // Windows 11 variable faces give controls a calmer, more deliberate
    // rhythm while preserving a safe Segoe fallback on older systems.
    readonly property string displayFont: "Segoe UI Variable Display"
    readonly property string uiFont: "Segoe UI Variable Text"
    // Deliberately denser face for interactive labels. It keeps small actions
    // from looking faint against filled buttons and dark surfaces.
    readonly property string controlFont: "Segoe UI Semibold"
    readonly property string monoFont: "Cascadia Mono"
    readonly property string iconFont: "Segoe Fluent Icons"

    function setMode(name) {
        var n = String(name || "midnight").toLowerCase()
        mode = n
        if (n === "oled") { bg="#000000"; surface="#050506"; card="#0a0b0f"; cardHi="#10121a"; stroke="#1b2030"; primary="#6192ff"; primaryDark="#3d6ed9"; accent="#bd9cff"; text="#f7f8fc"; muted="#a7afc0"; faint="#667087" }
        else if (n === "dark") { bg="#111318"; surface="#181c25"; card="#1c2230"; cardHi="#252d3d"; stroke="#303b50"; primary="#5b96ff"; primaryDark="#3d73dc"; accent="#a287ff"; text="#f6f7fb"; muted="#adb4c4"; faint="#778197" }
        else if (n === "ocean") { bg="#061418"; surface="#0a2027"; card="#102a33"; cardHi="#153842"; stroke="#24505a"; primary="#42c5dc"; primaryDark="#249db6"; accent="#82e1d0"; text="#effdff"; muted="#a6c8ca"; faint="#668d93" }
        else if (n === "violet") { bg="#10091a"; surface="#1a1030"; card="#231642"; cardHi="#2d1d52"; stroke="#47316d"; primary="#a577ff"; primaryDark="#8054dc"; accent="#ff91c6"; text="#fcf6ff"; muted="#c7b5d9"; faint="#8d77a6" }
        else if (n === "aurora") { bg="#07111f"; surface="#0b1d31"; card="#102842"; cardHi="#143655"; stroke="#24547a"; primary="#58c9ff"; primaryDark="#319bd4"; accent="#92f0d2"; text="#effaff"; muted="#a8c7d8"; faint="#668da6" }
        else if (n === "forest") { bg="#07160f"; surface="#0c2419"; card="#123222"; cardHi="#19422d"; stroke="#286144"; primary="#58d69a"; primaryDark="#2da86d"; accent="#b7ee71"; text="#f0fff5"; muted="#a7cdb4"; faint="#668e76" }
        else if (n === "ember") { bg="#130e0c"; surface="#1d1512"; card="#261a16"; cardHi="#31211b"; stroke="#55372d"; primary="#ff8967"; primaryDark="#d85d41"; accent="#f5bb72"; text="#fff7f2"; muted="#d9b9ab"; faint="#9d796d" }
        else if (n === "sapphire") { bg="#071027"; surface="#0b1938"; card="#10244c"; cardHi="#17305f"; stroke="#294a87"; primary="#5d9dff"; primaryDark="#3676dc"; accent="#b4a5ff"; text="#f3f7ff"; muted="#b2c4e6"; faint="#748bb4" }
        else if (n === "rose") { bg="#1b0917"; surface="#2a1028"; card="#3b1638"; cardHi="#512047"; stroke="#783968"; primary="#fa72bb"; primaryDark="#d64d99"; accent="#f5bd72"; text="#fff4fb"; muted="#e3b7d2"; faint="#a77898" }
        else if (n === "coral") { bg="#1b0c12"; surface="#2b121d"; card="#401a29"; cardHi="#552033"; stroke="#7f3951"; primary="#ff7b8b"; primaryDark="#dc5268"; accent="#ffc17a"; text="#fff5f6"; muted="#e7b9c2"; faint="#a97a86" }
        else if (n === "lime") { bg="#0e1708"; surface="#17240e"; card="#213417"; cardHi="#2b4520"; stroke="#4b7135"; primary="#9de85b"; primaryDark="#6fbb38"; accent="#f4db62"; text="#f6ffed"; muted="#c2d9ad"; faint="#829c70" }
        else if (n === "cobalt") { bg="#070d24"; surface="#0c1640"; card="#12215d"; cardHi="#193077"; stroke="#3353a4"; primary="#5f8fff"; primaryDark="#416fe1"; accent="#79d8ff"; text="#f2f6ff"; muted="#b8c8ef"; faint="#788ab8" }
        else if (n === "sunset") { bg="#1d0d08"; surface="#2f160f"; card="#452017"; cardHi="#592b1e"; stroke="#7c4830"; primary="#ff9d5c"; primaryDark="#db6b37"; accent="#f8d05d"; text="#fff8f1"; muted="#e7c2aa"; faint="#aa8068" }
        else if (n === "light") { bg="#f6f8fc"; surface="#ffffff"; card="#ffffff"; cardHi="#eef3ff"; stroke="#d8e0ee"; primary="#2667da"; primaryDark="#1f56bd"; accent="#7057da"; text="#14213a"; muted="#60708c"; faint="#8290a8" }
        else { mode="midnight"; bg="#070a14"; surface="#0d1427"; card="#121c33"; cardHi="#182542"; stroke="#293958"; primary="#6697ff"; primaryDark="#4978ec"; accent="#b392ff"; text="#f4f7ff"; muted="#a4b0ca"; faint="#697899" }
    }
}
