import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    property string title: root.t("Biblioteca", "Library")
    property string subtitle: ""
    property var entryModel
    property string actionKind: "favorite"
    implicitHeight: libraryContent.implicitHeight
    function t(spanish, english) { return wizz.language === "en" ? english : spanish }
    Column {
        id: libraryContent
        width: parent.width; spacing: 16
        RowLayout {
            width: parent.width
            ColumnLayout { Layout.fillWidth: true; spacing: 3
                Text { text: root.title; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 28; font.weight: Font.Bold }
                Text { text: root.subtitle; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 13 }
            }
            PressSurface {
                Layout.preferredWidth: 148; Layout.preferredHeight: 38; radius: 19; accentColor: Theme.primary
                color: "transparent"; border.color: Theme.primary; visible: root.actionKind !== "favorite"; onClicked: wizz.refresh()
                Row { anchors.centerIn: parent; spacing: 7; AppIcon { anchors.verticalCenter: parent.verticalCenter; width: 14; height: 14; name: root.actionKind === "routine" ? "plus" : "star"; color: Theme.primary } Text { text: root.actionKind === "routine" ? root.t("Nueva", "New") : root.t("Guardar actual", "Save current"); color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.DemiBold } }
            }
        }
        Rectangle { width: parent.width; height: 48; radius: Theme.radiusMedium; color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.10); border.width: 1; border.color: Theme.stroke; visible: root.actionKind !== "favorite"; Text { anchors.verticalCenter: parent.verticalCenter; anchors.left: parent.left; anchors.leftMargin: 16; text: root.actionKind === "routine" ? root.t("Crea secuencias fáciles con acciones, esperas y destinos.", "Build simple sequences with actions, delays, and targets.") : root.t("Explora los modos WiZ y guarda tus combinaciones favoritas.", "Explore WiZ modes and save your favorite combinations."); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 12 } }
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
                    Rectangle { x: 18; y: 18; width: 42; height: 42; radius: 14; color: Qt.rgba(entryColor.r, entryColor.g, entryColor.b, 0.18); AppIcon { anchors.centerIn: parent; width: 21; height: 21; name: root.actionKind === "favorite" ? "star" : root.actionKind === "scene" ? "sparkles" : "routines"; color: entryColor } }
                    Column { x: 18; y: 78; spacing: 3; Text { text: title; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 14; font.weight: Font.DemiBold } Text { text: subtitle; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize } }
                }
            }
        }
    }
}
