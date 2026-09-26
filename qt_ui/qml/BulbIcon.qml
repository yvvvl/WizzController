import QtQuick

Item {
    id: root
    property color iconColor: "white"
    implicitWidth: 24
    implicitHeight: 24

    // A small vector bulb drawn by QML: it is bundled with the application
    // and therefore cannot turn into a missing-glyph square on another PC.
    Rectangle {
        x: root.width * 0.25; y: root.height * 0.06
        width: root.width * 0.50; height: root.height * 0.58
        radius: width * 0.50
        color: "transparent"; border.width: Math.max(1.5, root.width * 0.075)
        border.color: root.iconColor
    }
    Rectangle { x: root.width * 0.38; y: root.height * 0.57; width: root.width * 0.24; height: root.height * 0.18; radius: 2; color: root.iconColor }
    Rectangle { x: root.width * 0.31; y: root.height * 0.77; width: root.width * 0.38; height: root.height * 0.08; radius: 2; color: root.iconColor }
    Rectangle { x: root.width * 0.35; y: root.height * 0.89; width: root.width * 0.30; height: root.height * 0.07; radius: 2; color: root.iconColor }
}
