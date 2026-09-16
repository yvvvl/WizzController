import QtQuick

Rectangle {
    id: root
    property alias mouseArea: pointer
    property bool selected: false
    property color accentColor: Theme.primary
    property bool elevated: false
    // Ghost controls (icons, close actions) intentionally have no ring until
    // hovered. Use `outlined: true` only for a deliberate secondary action.
    property bool outlined: false
    // The former one-pixel shine looked like a stray white seam on compact
    // controls in dark and saturated themes. Depth now comes from the border,
    // hover colour and contained press overlay instead.
    property bool showTopHighlight: false
    signal clicked()

    radius: Theme.radiusMedium
    antialiasing: true
    color: selected
        ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.14)
        : pointer.containsMouse ? Theme.cardHi : Theme.card
    border.width: root.outlined || root.selected || root.color.a > 0.01 ? 1 : 0
    border.color: selected
        ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.62)
        : pointer.containsMouse ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.58) : Theme.stroke
    // Every visual layer is kept inside the same rounded outline.  A subtle
    // press is enough feedback; enlarging on hover made neighbouring buttons
    // look misaligned and exposed square edges on dense toolbars.
    clip: true
    scale: pointer.pressed ? 0.99 : 1
    transformOrigin: Item.Center

    // Optional only for a deliberate glossy surface; ordinary actions keep a
    // clean, flat top edge so neighbouring controls align visually.
    Rectangle {
        visible: root.showTopHighlight && root.color.a > 0.01
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
        anchors.leftMargin: 1; anchors.rightMargin: 1; anchors.topMargin: 1
        height: 1
        radius: root.radius
        color: Qt.rgba(Theme.highlight.r, Theme.highlight.g, Theme.highlight.b,
                       root.selected ? 0.16 : pointer.containsMouse ? 0.10 : 0.055)
    }

    Rectangle {
        id: pressOverlay
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, root.radius - 1)
        antialiasing: true
        color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 1)
        opacity: 0
    }

    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
        onPressed: {
            pressOverlay.opacity = 0.18
        }
        onReleased: releaseFade.restart()
        onCanceled: releaseFade.restart()
        onClicked: root.clicked()
    }

    Timer { id: releaseFade; interval: 120; onTriggered: fade.restart() }
    NumberAnimation { id: fade; target: pressOverlay; property: "opacity"; to: 0; duration: Theme.motionFast; easing.type: Easing.OutCubic }

    Behavior on color { ColorAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } }
    Behavior on border.color { ColorAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } }
    Behavior on scale { NumberAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } }
}
