pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

Item {
    id: root
    implicitHeight: 446
    property real hue: 0.67
    property real whiteness: 0.06
    property int kelvin: wizz.whiteKelvin
    property color previewColor: wizz.colorHex
    property int pendingRed: 255
    property int pendingGreen: 255
    property int pendingBlue: 255
    property bool rgbDirty: false
    property bool whiteDirty: false

    function rgbHex(red, green, blue) {
        function channel(value) { return Math.max(0, Math.min(255, value)).toString(16).padStart(2, "0") }
        return "#" + channel(red) + channel(green) + channel(blue)
    }

    function flushPreview() {
        if (rgbDirty) {
            rgbDirty = false
            wizz.setRgb(pendingRed, pendingGreen, pendingBlue)
        }
        if (whiteDirty) {
            whiteDirty = false
            wizz.setWhite(kelvin)
        }
    }

    function schedulePreview() {
        if (!previewTransport.running)
            previewTransport.start()
    }

    Timer {
        id: previewTransport
        // One bridge crossing per rendered frame is enough; the selector itself
        // still follows every pointer event locally without waiting for Python.
        interval: 16
        repeat: false
        onTriggered: root.flushPreview()
    }

    function sendHex(hex) {
        var value = hex.substring(1)
        root.previewColor = hex
        wizz.setRgb(parseInt(value.substring(0, 2), 16),
                    parseInt(value.substring(2, 4), 16),
                    parseInt(value.substring(4, 6), 16))
        wizz.commitCurrentColor()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Text { text: "PALETA HUE / PUREZA"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11; font.weight: Font.Bold }
            Item { Layout.fillWidth: true }
            Text { text: "HEX"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 10; font.weight: Font.Bold }
        }
        Text { text: "Horizontal: matiz · vertical: pureza perceptual · sin negro"; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: 11 }

        Rectangle {
            id: spectrum
            objectName: "colorSpectrum"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(142, width / 3)
            radius: 14
            antialiasing: true
            clip: true
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.00; color: "#ff2b20" }
                GradientStop { position: 0.16; color: "#fff000" }
                GradientStop { position: 0.33; color: "#39f51c" }
                GradientStop { position: 0.50; color: "#10e9ec" }
                GradientStop { position: 0.67; color: "#1c45ff" }
                GradientStop { position: 0.84; color: "#cd27ff" }
                GradientStop { position: 1.00; color: "#ff2870" }
            }
            Rectangle {
                anchors.fill: parent
                radius: spectrum.radius
                antialiasing: true
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.00; color: "#ffffff" }
                    GradientStop { position: 0.78; color: "#00ffffff" }
                    GradientStop { position: 1.00; color: "#00ffffff" }
                }
            }
            Rectangle {
                width: 22; height: 22; radius: 11
                x: Math.max(0, Math.min(spectrum.width - width, spectrum.width * root.hue - width / 2))
                y: Math.max(0, Math.min(spectrum.height - height, spectrum.height * root.whiteness - height / 2))
                color: root.previewColor
                border.width: 2; border.color: "white"
            }
            MouseArea {
                id: spectrumPointer
                anchors.fill: parent
                cursorShape: Qt.CrossCursor
                preventStealing: true
                onPressed: (mouse) => updateColor(mouse.x, mouse.y)
                onPositionChanged: (mouse) => { if (pressed) updateColor(mouse.x, mouse.y) }
                onReleased: { root.flushPreview(); wizz.commitCurrentColor() }
                function updateColor(px, py) {
                    root.hue = Math.max(0, Math.min(1, px / width))
                    root.whiteness = Math.max(0, Math.min(1, py / height))
                    var h = root.hue * 6
                    var x = 1 - Math.abs(h % 2 - 1)
                    var r = 0; var g = 0; var b = 0
                    if (h < 1) { r = 1; g = x }
                    else if (h < 2) { r = x; g = 1 }
                    else if (h < 3) { g = 1; b = x }
                    else if (h < 4) { g = x; b = 1 }
                    else if (h < 5) { r = x; b = 1 }
                    else { r = 1; b = x }
                    var white = 1 - root.whiteness
                    root.pendingRed = Math.round((r + (1-r)*white) * 255)
                    root.pendingGreen = Math.round((g + (1-g)*white) * 255)
                    root.pendingBlue = Math.round((b + (1-b)*white) * 255)
                    root.previewColor = root.rgbHex(root.pendingRed, root.pendingGreen, root.pendingBlue)
                    root.rgbDirty = true
                    root.schedulePreview()
                }
            }
        }

        Connections {
            target: wizz
            function onColorChanged() {
                if (!spectrumPointer.pressed)
                    root.previewColor = wizz.colorHex
            }
        }

        RowLayout {
            Layout.fillWidth: true; spacing: 12
            PressSurface {
                Layout.preferredWidth: 38; Layout.preferredHeight: 38; radius: 19
                color: wizz.currentFavoriteSaved && wizz.colorMode === "rgb" ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.20) : Theme.cardHi
                accentColor: Theme.primary
                onClicked: wizz.saveCurrentFavorite()
                Text { anchors.centerIn: parent; text: wizz.currentFavoriteSaved && wizz.colorMode === "rgb" ? "♥" : "♡"; color: Theme.primary; font.pixelSize: 21 }
            }
            Repeater {
                model: ["#6120f5", "#ff5f82"]
                delegate: PressSurface { required property string modelData; Layout.preferredWidth: 38; Layout.preferredHeight: 38; radius: 19; color: modelData; accentColor: modelData; border.width: 0; onClicked: root.sendHex(modelData) }
            }
            Rectangle {
                Layout.preferredWidth: 88; Layout.preferredHeight: 30; radius: 15
                color: Theme.cardHi; border.width: 1; border.color: Theme.stroke
                Text { anchors.centerIn: parent; text: String(root.previewColor).toUpperCase(); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold }
            }
            Item { Layout.fillWidth: true }
        }

        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke }
        Text { text: "BLANCOS CCT"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11; font.weight: Font.Bold }
        Rectangle {
            id: cctTrack
            Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 12
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#ffe0a5" }
                GradientStop { position: 0.5; color: "#fffdf4" }
                GradientStop { position: 1; color: "#d8efff" }
            }
            Rectangle { x: Math.max(0, Math.min(parent.width-width, (root.kelvin-2200)/4300*parent.width-width/2)); y: 5; width: 24; height: 24; radius: 12; color: "#fff"; border.width: 2; border.color: "#b6a58e" }
            MouseArea { anchors.fill: parent; preventStealing: true; onPressed: (mouse) => updateWhite(mouse.x); onPositionChanged: (mouse) => { if (pressed) updateWhite(mouse.x) }; onReleased: { root.flushPreview(); wizz.commitWhite(root.kelvin) } function updateWhite(px) { root.kelvin = Math.round(2200 + Math.max(0,Math.min(1,px/width))*4300); root.whiteDirty = true; root.schedulePreview() } }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 12
            PressSurface {
                Layout.preferredWidth: 38; Layout.preferredHeight: 38; radius: 19
                color: wizz.currentFavoriteSaved && wizz.colorMode === "white" ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.20) : Theme.cardHi
                accentColor: Theme.primary
                onClicked: wizz.saveCurrentFavorite()
                Text { anchors.centerIn: parent; text: wizz.currentFavoriteSaved && wizz.colorMode === "white" ? "♥" : "♡"; color: Theme.primary; font.pixelSize: 21 }
            }
            Repeater { model: [{c:"#edf8ff",k:6500},{c:"#ffe9b5",k:2700}]; delegate: PressSurface { required property var modelData; Layout.preferredWidth: 38; Layout.preferredHeight: 38; radius: 19; color: modelData.c; accentColor: modelData.c; border.width: 0; onClicked: { root.kelvin=modelData.k; wizz.setWhite(modelData.k); wizz.commitWhite(modelData.k) } } }
            Rectangle {
                Layout.preferredWidth: 88; Layout.preferredHeight: 30; radius: 15
                color: Theme.cardHi; border.width: 1; border.color: Theme.stroke
                Text { anchors.centerIn: parent; text: root.kelvin + "K"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold }
            }
            Item { Layout.fillWidth: true }
        }
    }
}
