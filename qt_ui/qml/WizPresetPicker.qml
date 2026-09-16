import QtQuick
import QtQuick.Controls.Basic

// Visual input for local preset editors.  It intentionally does not call the
// bridge: the owning form decides when to save, while HEX/Kelvin remains the
// precise, editable representation of the same value.
Item {
    id: root
    implicitHeight: mode === "rgb" ? 118 : 76
    property string mode: "rgb"
    property string selection: "#FF4FA3"
    signal picked(string value)

    function clamp(value, lower, upper) { return Math.max(lower, Math.min(upper, value)) }
    function channel(value) { return Math.round(clamp(value, 0, 255)).toString(16).padStart(2, "0") }
    function rgbHex(red, green, blue) { return "#" + channel(red) + channel(green) + channel(blue) }
    function colorAt(x, y, width, height) {
        const hue = clamp(x / width, 0, 1) * 6
        // The plane is intentionally white at the top and fully saturated at
        // the bottom.  The previous inverse mapping could produce black at
        // the bottom edge, even though no black exists in the rendered plane.
        const saturation = clamp(y / height, 0, 1)
        const chroma = saturation
        const secondary = chroma * (1 - Math.abs(hue % 2 - 1))
        const base = 1 - chroma
        let red = 0; let green = 0; let blue = 0
        if (hue < 1) { red = chroma; green = secondary }
        else if (hue < 2) { red = secondary; green = chroma }
        else if (hue < 3) { green = chroma; blue = secondary }
        else if (hue < 4) { green = secondary; blue = chroma }
        else if (hue < 5) { red = secondary; blue = chroma }
        else { red = chroma; blue = secondary }
        return rgbHex((red + base) * 255, (green + base) * 255, (blue + base) * 255).toUpperCase()
    }
    function rgbPosition() {
        if (!/^#[0-9a-fA-F]{6}$/.test(selection))
            return { x: 0.92, y: 0.25 }
        const color = Qt.color(selection)
        const maxValue = Math.max(color.r, color.g, color.b)
        const minValue = Math.min(color.r, color.g, color.b)
        const delta = maxValue - minValue
        let hue = 0
        if (delta > 0) {
            if (maxValue === color.r) hue = ((color.g - color.b) / delta + (color.g < color.b ? 6 : 0)) / 6
            else if (maxValue === color.g) hue = ((color.b - color.r) / delta + 2) / 6
            else hue = ((color.r - color.g) / delta + 4) / 6
        }
        return { x: hue, y: maxValue ? delta / maxValue : 0 }
    }
    function setKelvin(position) { picked(String(Math.round(2200 + clamp(position, 0, 1) * 4300))) }

    Column {
        anchors.fill: parent
        spacing: 7
        visible: root.mode === "rgb"
        Text { text: "SELECTOR DE COLOR"; color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 0.7 }
        Rectangle {
            id: rgbPlane
            width: parent.width; height: 94; radius: 12; clip: true
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#ff2d2d" } GradientStop { position: .17; color: "#fff000" }
                GradientStop { position: .34; color: "#38f51d" } GradientStop { position: .5; color: "#12e9ed" }
                GradientStop { position: .67; color: "#1e49ff" } GradientStop { position: .84; color: "#cc29ff" } GradientStop { position: 1; color: "#ff2d71" }
            }
            Rectangle {
                anchors.fill: parent; radius: parent.radius
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    // The interaction maps the top edge to white and the
                    // bottom edge to the pure hue. Keep the rendered plane
                    // in that same direction so the cursor never lies.
                    GradientStop { position: 0; color: "#ffffffff" }
                    GradientStop { position: 1; color: "#00ffffff" }
                }
            }
            Rectangle {
                readonly property var position: root.rgbPosition()
                width: 18; height: 18; radius: 9
                x: root.clamp(position.x * rgbPlane.width - width / 2, 0, rgbPlane.width - width)
                y: root.clamp(position.y * rgbPlane.height - height / 2, 0, rgbPlane.height - height)
                color: root.selection; border.width: 2; border.color: "white"
            }
            MouseArea {
                anchors.fill: parent; cursorShape: Qt.CrossCursor
                onPressed: function(mouse) { root.picked(root.colorAt(mouse.x, mouse.y, width, height)) }
                onPositionChanged: function(mouse) { if (pressed) root.picked(root.colorAt(mouse.x, mouse.y, width, height)) }
            }
        }
    }

    Column {
        anchors.fill: parent
        spacing: 7
        visible: root.mode === "white"
        Text { text: "SELECTOR DE BLANCO"; color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 0.7 }
        Rectangle {
            id: whiteTrack
            width: parent.width; height: 38; radius: 13
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#ffd895" }
                GradientStop { position: .5; color: "#fffdf6" }
                GradientStop { position: 1; color: "#d7efff" }
            }
            Rectangle {
                readonly property real kelvin: Number(root.selection || 4000)
                width: 22; height: 22; radius: 11
                x: root.clamp((kelvin - 2200) / 4300 * whiteTrack.width - width / 2, 0, whiteTrack.width - width)
                anchors.verticalCenter: parent.verticalCenter
                color: "white"; border.width: 2; border.color: "#b9aa91"
            }
            MouseArea {
                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                onPressed: function(mouse) { root.setKelvin(mouse.x / width) }
                onPositionChanged: function(mouse) { if (pressed) root.setKelvin(mouse.x / width) }
            }
        }
        Row {
            width: parent.width
            Text { text: "2200K"; color: Theme.faint; font.pixelSize: 9 }
            Text { width: parent.width - 76; text: "Neutro"; horizontalAlignment: Text.AlignHCenter; color: Theme.faint; font.pixelSize: 9 }
            Text { text: "6500K"; color: Theme.faint; font.pixelSize: 9 }
        }
    }
}
