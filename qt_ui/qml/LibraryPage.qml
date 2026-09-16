import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    property string title: "Biblioteca"
    property string subtitle: ""
    property var entryModel
    property string actionKind: "favorite"
    implicitHeight: libraryContent.implicitHeight
    Column {
        id: libraryContent
        width: parent.width; spacing: 16
        RowLayout {
            width: parent.width
            ColumnLayout { Layout.fillWidth: true; spacing: 3
                Text { text: root.title; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 28; font.weight: Font.Bold }
                Text { text: root.subtitle; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 13 }
            }
            PressSurface { Layout.preferredWidth: 128; Layout.preferredHeight: 38; radius: 19; accentColor: Theme.primary; color: "transparent"; border.color: Theme.primary; visible: root.actionKind !== "favorite"; onClicked: wizz.refresh(); Text { anchors.centerIn: parent; text: root.actionKind === "routine" ? "+  Nueva" : "☆  Guardar actual"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.DemiBold } }
        }
        Rectangle { width: parent.width; height: 48; radius: Theme.radiusMedium; color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.10); border.width: 1; border.color: Theme.stroke; visible: root.actionKind !== "favorite"; Text { anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 16; text: root.actionKind === "routine" ? "Crea secuencias fáciles con acciones, esperas y destinos." : "Explora los modos WiZ y guarda tus combinaciones favoritas."; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 12 } }
        GridLayout {
            width: parent.width; columns: width >= 980 ? 4 : width >= 640 ? 3 : 2; columnSpacing: 12; rowSpacing: 12
            Repeater {
                model: root.entryModel
                delegate: PressSurface {
                    required property string title
                    required property string subtitle
                    required property color entryColor
                    required property string uid
                    Layout.fillWidth: true; implicitHeight: 132; accentColor: entryColor
                    onClicked: { if (root.actionKind === "favorite") wizz.applyFavorite(uid); else if (root.actionKind === "scene") wizz.applyScene(uid); else wizz.runRoutine(uid) }
                    Rectangle { x: 18; y: 18; width: 42; height: 42; radius: 14; color: Qt.rgba(entryColor.r, entryColor.g, entryColor.b, 0.18); Text { anchors.centerIn: parent; text: root.actionKind === "favorite" ? "★" : root.actionKind === "scene" ? "✦" : "↯"; color: entryColor; font.family: Theme.uiFont; font.pixelSize: 21 } }
                    Column { x: 18; y: 78; spacing: 3; Text { text: title; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: subtitle; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 11 } }
                }
            }
        }
    }
}
