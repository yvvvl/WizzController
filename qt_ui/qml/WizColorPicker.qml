pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

Item {
    id: root
    implicitHeight: selectorContent.implicitHeight
    property bool selectionOnly: false
    property bool showColorSection: true
    property bool showWhiteSection: true
    property string selectedHex: "#FF0000"
    property int selectedKelvin: 2700
    signal colorSelected(string hex)
    signal whiteSelected(int kelvin)
    property real hue: 0.67
    property real whiteness: 0.06
    property int kelvin: selectionOnly ? selectedKelvin : wizz.whiteKelvin
    property color previewColor: selectionOnly ? selectedHex : wizz.colorHex
    property int pendingRed: 255
    property int pendingGreen: 255
    property int pendingBlue: 255
    property bool rgbDirty: false
    property bool whiteDirty: false

    function rgbHex(red, green, blue) {
        function channel(value) { return Math.max(0, Math.min(255, value)).toString(16).padStart(2, "0") }
        return "#" + channel(red) + channel(green) + channel(blue)
    }

    function syncSelectionMarker(hex) {
        if (!selectionOnly || !/^#[0-9a-fA-F]{6}$/.test(String(hex))) return
        const color = Qt.color(hex)
        const red = color.r; const green = color.g; const blue = color.b
        const high = Math.max(red, green, blue)
        const low = Math.min(red, green, blue)
        const spread = high - low
        let position = 0
        if (spread > 0) {
            if (high === red) position = ((green - blue) / spread + 6) % 6
            else if (high === green) position = (blue - red) / spread + 2
            else position = (red - green) / spread + 4
        }
        hue = position / 6
        whiteness = 1 - low
    }

    onSelectedHexChanged: syncSelectionMarker(selectedHex)
    Component.onCompleted: syncSelectionMarker(selectedHex)

    function flushPreview() {
        if (rgbDirty) {
            rgbDirty = false
            if (selectionOnly) {
                selectedHex = String(previewColor).toUpperCase()
                colorSelected(selectedHex)
            } else {
                wizz.setRgb(pendingRed, pendingGreen, pendingBlue)
            }
        }
        if (whiteDirty) {
            whiteDirty = false
            if (selectionOnly) {
                selectedKelvin = kelvin
                whiteSelected(kelvin)
            } else {
                wizz.setWhite(kelvin)
            }
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
        if (selectionOnly) {
            selectedHex = hex.toUpperCase()
            colorSelected(selectedHex)
            return
        }
        wizz.setRgb(parseInt(value.substring(0, 2), 16),
                    parseInt(value.substring(2, 4), 16),
                    parseInt(value.substring(4, 6), 16))
        wizz.commitCurrentColor()
    }

    function chooseKelvin(value) {
        root.kelvin = Math.max(2200, Math.min(6500, Math.round(value)))
        if (selectionOnly) {
            selectedKelvin = root.kelvin
            whiteSelected(root.kelvin)
        } else {
            wizz.setWhite(root.kelvin)
            wizz.commitWhite(root.kelvin)
        }
    }

    ColumnLayout {
        id: selectorContent
        anchors.fill: parent
        spacing: 10

        RowLayout {
            visible: root.showColorSection
            Layout.fillWidth: true
            Text { text: wizz.language === "en" ? "HUE / SATURATION PALETTE" : "PALETA HUE / PUREZA"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
            Item { Layout.fillWidth: true }
            Text { text: "HEX"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
        }
        Text { visible: root.showColorSection; text: wizz.language === "en" ? "Horizontal: hue · vertical: perceptual saturation · no black" : "Horizontal: matiz · vertical: pureza perceptual · sin negro"; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize }

        Rectangle {
            id: spectrum
            objectName: "colorSpectrum"
            visible: root.showColorSection
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
                onReleased: { root.flushPreview(); if (!root.selectionOnly) wizz.commitCurrentColor() }
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
                if (!root.selectionOnly && !spectrumPointer.pressed)
                    root.previewColor = wizz.colorHex
            }
        }

        RowLayout {
            visible: root.showColorSection
            Layout.fillWidth: true; spacing: 10
            PressSurface {
                visible: !root.selectionOnly
                Layout.preferredWidth: 132; Layout.preferredHeight: 36; radius: 18
                color: wizz.currentFavoriteSaved && wizz.colorMode === "rgb" ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.20) : Theme.cardHi
                accentColor: Theme.primary
                outlined: true
                onClicked: wizz.saveCurrentFavorite()
                Row { anchors.centerIn: parent; spacing: 7; AppIcon { anchors.verticalCenter: parent.verticalCenter; width: 15; height: 15; name: "heart"; color: Theme.primary; filled: wizz.currentFavoriteSaved && wizz.colorMode === "rgb" } Text { text: wizz.currentFavoriteSaved && wizz.colorMode === "rgb" ? (wizz.language === "en" ? "Saved" : "Guardado") : (wizz.language === "en" ? "Save favorite" : "Guardar favorito"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold } }
            }
            Rectangle {
                Layout.preferredWidth: 88; Layout.preferredHeight: 30; radius: 15
                color: Theme.cardHi; border.width: 1; border.color: Theme.stroke
                Text { anchors.centerIn: parent; text: String(root.previewColor).toUpperCase(); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
            }
            Item { Layout.fillWidth: true }
        }

        Rectangle { visible: root.showColorSection && root.showWhiteSection; Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke }
        Text { visible: root.showWhiteSection; text: wizz.language === "en" ? "CCT WHITES" : "BLANCOS CCT"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
        Rectangle {
            id: cctTrack
            objectName: "whiteCctTrack"
            visible: root.showWhiteSection
            Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 12
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#ffe0a5" }
                GradientStop { position: 0.5; color: "#fffdf4" }
                GradientStop { position: 1; color: "#d8efff" }
            }
            Rectangle { x: Math.max(0, Math.min(parent.width-width, (root.kelvin-2200)/4300*parent.width-width/2)); y: 5; width: 24; height: 24; radius: 12; color: "#fff"; border.width: 2; border.color: "#b6a58e" }
            MouseArea { anchors.fill: parent; preventStealing: true; onPressed: (mouse) => updateWhite(mouse.x); onPositionChanged: (mouse) => { if (pressed) updateWhite(mouse.x) }; onReleased: { root.flushPreview(); if (!root.selectionOnly) wizz.commitWhite(root.kelvin) } function updateWhite(px) { root.kelvin = Math.round(2200 + Math.max(0,Math.min(1,px/width))*4300); root.whiteDirty = true; root.schedulePreview() } }
        }
        Flow {
            id: presetFlow
            visible: root.showWhiteSection
            Layout.fillWidth: true
            Layout.preferredHeight: childrenRect.height
            spacing: 8
            PressSurface {
                visible: !root.selectionOnly
                width: 132; height: 36; radius: 18
                color: wizz.currentFavoriteSaved && wizz.colorMode === "white" ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.20) : Theme.cardHi
                accentColor: Theme.primary
                outlined: true
                onClicked: wizz.saveCurrentFavorite()
                Row { anchors.centerIn: parent; spacing: 7; AppIcon { anchors.verticalCenter: parent.verticalCenter; width: 15; height: 15; name: "heart"; color: Theme.primary; filled: wizz.currentFavoriteSaved && wizz.colorMode === "white" } Text { text: wizz.currentFavoriteSaved && wizz.colorMode === "white" ? (wizz.language === "en" ? "Saved" : "Guardado") : (wizz.language === "en" ? "Save favorite" : "Guardar favorito"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold } }
            }
            PressSurface {
                width: 116; height: 36; radius: 18
                color: Theme.cardHi; accentColor: Theme.warning; outlined: true
                onClicked: root.chooseKelvin(2700)
                Row { anchors.centerIn: parent; spacing: 6; Rectangle { anchors.verticalCenter: parent.verticalCenter; width: 11; height: 11; radius: 6; color: "#ffe0a5" } Text { text: wizz.language === "en" ? "Warm · 2700 K" : "Cálido · 2700 K"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold } }
            }
            PressSurface {
                width: 140; height: 36; radius: 18
                color: Theme.cardHi; accentColor: Theme.primary; outlined: true
                onClicked: root.chooseKelvin(6500)
                Row { anchors.centerIn: parent; spacing: 6; Rectangle { anchors.verticalCenter: parent.verticalCenter; width: 11; height: 11; radius: 6; color: "#d8efff" } Text { text: wizz.language === "en" ? "Cool White · 6500 K" : "Blanco frío · 6500 K"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold } }
            }
            Rectangle {
                width: 88; height: 30; radius: 15
                color: Theme.cardHi; border.width: 1; border.color: Theme.stroke
                Text { anchors.centerIn: parent; text: root.kelvin + " K"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
            }
        }
    }
}
