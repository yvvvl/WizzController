pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    objectName: "colorPage"
    implicitHeight: pageContent.implicitHeight

    function activeName() {
        return wizz.colorMode === "white" ? "Blanco " + wizz.whiteKelvin + "K" : "Color " + wizz.colorHex.toUpperCase()
    }

    function activeSubtitle() {
        return (wizz.colorMode === "white" ? "Temperatura WiZ" : "Color RGB") + " · Brillo " + wizz.brightness + "%"
    }

    function applyExactValue(value) {
        if (wizz.colorMode === "white") {
            const kelvin = Number(value)
            if (kelvin >= 2200 && kelvin <= 6500) {
                wizz.setWhite(kelvin)
                wizz.commitWhite(kelvin)
            }
        } else {
            wizz.setHex(value)
        }
    }

    ColumnLayout {
        id: pageContent
        width: parent.width
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                Text { text: "Color Studio"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 30; font.weight: Font.Bold }
                Text { text: "Color puro, blancos Kelvin y brillo independiente"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 13 }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: root.width >= 800 ? 2 : 1
            columnSpacing: 16; rowSpacing: 14

            Rectangle {
                Layout.fillWidth: true; Layout.preferredWidth: root.width >= 800 ? root.width * 0.65 : root.width
                Layout.preferredHeight: 510; radius: Theme.radiusMedium
                color: Theme.card; border.width: 1; border.color: Theme.stroke
                WizColorPicker { anchors.fill: parent; anchors.margins: 18 }
            }

            Rectangle {
                Layout.fillWidth: true; Layout.preferredWidth: root.width >= 800 ? root.width * 0.35 : root.width
                Layout.preferredHeight: 306; Layout.alignment: Qt.AlignTop
                radius: Theme.radiusMedium; color: Theme.card; border.width: 1; border.color: Theme.stroke
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "BRILLO"; color: Theme.muted; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 0.8 }
                        Item { Layout.fillWidth: true }
                        Text { text: Math.round(level.value) + "%"; color: Theme.text; font.pixelSize: 20; font.weight: Font.Bold }
                    }
                    Text { text: "Dimming real de la ampolleta"; color: Theme.faint; font.pixelSize: 11 }
                    Slider {
                        id: level
                        Layout.fillWidth: true; from: 10; to: 100; value: wizz.brightness
                        onMoved: wizz.queueBrightness(Math.round(value))
                        background: Rectangle {
                            x: level.leftPadding; y: level.topPadding + level.availableHeight / 2 - height / 2
                            width: level.availableWidth; height: 6; radius: 3; color: Theme.stroke
                            Rectangle { width: level.visualPosition * parent.width; height: parent.height; radius: parent.radius; gradient: Gradient { GradientStop { position: 0; color: Theme.primary } GradientStop { position: 1; color: Theme.accent } } }
                        }
                        handle: Rectangle { x: level.leftPadding + level.visualPosition * (level.availableWidth - width); y: level.topPadding + level.availableHeight / 2 - height / 2; width: 21; height: 21; radius: 11; color: Theme.text; border.width: 2; border.color: Theme.card }
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 7
                        Repeater {
                            model: [10, 25, 50, 75, 100]
                            delegate: PressSurface {
                                required property int modelData
                                Layout.fillWidth: true; Layout.preferredHeight: 29; radius: 14
                                color: Math.round(level.value) === modelData ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.18) : "transparent"
                                border.color: Math.round(level.value) === modelData ? Theme.primary : Theme.stroke
                                accentColor: Theme.primary
                                onClicked: { level.value = modelData; wizz.queueBrightness(modelData) }
                                Text { anchors.centerIn: parent; text: modelData + "%"; color: Theme.text; font.pixelSize: 9; font.weight: Font.DemiBold }
                            }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 10
                        Rectangle { Layout.preferredWidth: 28; Layout.preferredHeight: 28; radius: 14; color: wizz.colorHex; border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.24) }
                        ColumnLayout { Layout.fillWidth: true; spacing: 1; Text { text: wizz.colorMode === "white" ? "Modo blanco" : "Modo color"; color: Theme.text; font.pixelSize: 11; font.weight: Font.DemiBold } Text { text: wizz.colorMode === "white" ? wizz.whiteKelvin + "K" : wizz.colorHex.toUpperCase(); color: Theme.faint; font.pixelSize: 10 } }
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 8
                        Text { text: wizz.colorMode === "white" ? "KELVIN EXACTO" : "HEX EXACTO"; color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold }
                        TextField {
                            id: exactValue
                            Layout.fillWidth: true; Layout.preferredHeight: 34
                            text: wizz.colorMode === "white" ? String(wizz.whiteKelvin) : wizz.colorHex.toUpperCase()
                            color: Theme.text; font.family: Theme.monoFont; font.pixelSize: 10; leftPadding: 10; rightPadding: 10
                            onAccepted: root.applyExactValue(text)
                            background: Rectangle { color: Theme.cardHi; radius: 10; border.width: 1; border.color: exactValue.activeFocus ? Theme.primary : Theme.stroke }
                        }
                        PressSurface {
                            Layout.preferredWidth: 66; Layout.preferredHeight: 34; radius: 17; color: "transparent"; outlined: true; border.color: Theme.stroke
                            onClicked: root.applyExactValue(exactValue.text)
                            Text { anchors.centerIn: parent; text: "Aplicar"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: recentContent.implicitHeight + 32
            radius: Theme.radiusMedium; color: Theme.card; border.width: 1; border.color: Theme.stroke
            ColumnLayout {
                id: recentContent
                anchors.fill: parent; anchors.margins: 16; spacing: 8
                RowLayout { Layout.fillWidth: true; Text { text: "RECIENTES"; color: Theme.muted; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 0.8 } Item { Layout.fillWidth: true } PressSurface { visible: recentRepeater.count > 0; Layout.preferredWidth: 62; Layout.preferredHeight: 26; radius: 13; color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.error; onClicked: wizz.clearRecents(); Text { anchors.centerIn: parent; text: "Limpiar"; color: Theme.muted; font.family: Theme.controlFont; font.pixelSize: 9; font.weight: Font.Bold } } }
                Text { text: "Últimos colores y blancos aplicados"; color: Theme.faint; font.pixelSize: 11 }
                Text { visible: recentRepeater.count === 0; text: "Aún no hay colores recientes. Aplica uno para guardarlo aquí."; color: Theme.faint; font.pixelSize: 11 }
                GridLayout {
                    // The history is capped at eight entries in the bridge;
                    // four columns intentionally produce a calm two-row grid.
                    Layout.fillWidth: true; columns: 4; columnSpacing: 8; rowSpacing: 8
                    Repeater {
                        id: recentRepeater; model: wizz.recentColorModel
                        delegate: PressSurface {
                            id: recentCard
                            required property string title; required property color entryColor; required property string uid
                            Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 11; accentColor: recentCard.entryColor
                            onClicked: wizz.applyRecent(recentCard.uid)
                            RowLayout { anchors.fill: parent; anchors.margins: 9; spacing: 7; Rectangle { Layout.preferredWidth: 18; Layout.preferredHeight: 18; radius: 9; color: recentCard.entryColor } Text { Layout.fillWidth: true; text: recentCard.title; color: Theme.text; font.pixelSize: 10; elide: Text.ElideRight } }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: favoriteContent.implicitHeight + 32
            radius: Theme.radiusMedium; color: Theme.card; border.width: 1; border.color: Theme.stroke
            ColumnLayout {
                id: favoriteContent
                anchors.fill: parent; anchors.margins: 16; spacing: 9
                RowLayout { Layout.fillWidth: true; Text { text: "FAVORITOS RÁPIDOS"; color: Theme.muted; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 0.8 } Item { Layout.fillWidth: true } Text { text: "Gestionar →"; color: Theme.primary; font.pixelSize: 10; MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: wizz.navigate(3) } } }
                Text { text: "Accesos guardados en WiZ"; color: Theme.faint; font.pixelSize: 11 }
                GridLayout {
                    Layout.fillWidth: true; columns: width >= 1120 ? 4 : width >= 600 ? 3 : 2; columnSpacing: 8; rowSpacing: 8
                    Repeater {
                        model: wizz.favoriteModel
                        delegate: PressSurface {
                            id: favoriteCard
                            required property string title; required property string subtitle; required property color entryColor; required property string uid
                            Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 12; accentColor: favoriteCard.entryColor
                            onClicked: wizz.applyFavorite(favoriteCard.uid)
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 10
                                Rectangle { Layout.preferredWidth: 18; Layout.preferredHeight: 18; radius: 9; color: favoriteCard.entryColor }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 0
                                    Text { Layout.fillWidth: true; text: favoriteCard.title; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 11; font.weight: Font.Bold; elide: Text.ElideRight }
                                    Text { Layout.fillWidth: true; text: favoriteCard.subtitle; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: 9; elide: Text.ElideRight }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
