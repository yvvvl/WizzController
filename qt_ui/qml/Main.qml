pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1120
    height: 760
    minimumWidth: 820
    minimumHeight: 600
    visible: true
    color: "transparent"
    flags: Qt.Window | Qt.FramelessWindowHint
    title: "WizZ Desktop"
    font.family: Theme.uiFont
    font.weight: 650

    property int currentPage: 0
    property int pendingPage: -1
    property bool pageVisible: false
    property bool qaOpenFavoriteEditor: false
    property string qaFavoriteEditorKind: ""
    property bool qaOpenSceneEditor: false
    property bool qaOpenRoutineEditor: false
    property bool qaOpenScheduleEditor: false
    property bool qaOpenScheduleTarget: false
    property var navigationItems: [
        {title: wizz.language === "en" ? "Home" : "Inicio", icon: "home"},
        {title: "Color", icon: "palette"},
        {title: wizz.language === "en" ? "Scenes" : "Escenas", icon: "scenes"},
        {title: wizz.language === "en" ? "Favorites" : "Favoritos", icon: "heart"},
        {title: wizz.language === "en" ? "Routines" : "Rutinas", icon: "routines"},
        {title: wizz.language === "en" ? "Settings" : "Ajustes", icon: "settings"},
        {title: "Hotkeys", icon: "keyboard"}
    ]
    property bool updateToastVisible: false
    property bool startupMinimizing: false
    readonly property int pageGutter: width < 960 ? 20 : 28
    readonly property int contentMaxWidth: 1420
    readonly property bool compactHeight: height < 740
    // Only a single configured bulb owns the logo colour. With several bulbs,
    // or when the light is off/unavailable, branding follows the chosen theme.
    readonly property color logoColor: wizz.liveBrandAccent && wizz.logoLightColor.length > 0
                                       ? wizz.logoLightColor : Theme.primary

    function navigateTo(index) {
        if (index === currentPage) return
        if (index === 0)
            wizz.refresh()
        // Switching pages must never wait for a decorative timer.  Heavy
        // pages such as Hotkeys are created immediately and only their entry
        // opacity animates, which makes the navigation feel responsive.
        pendingPage = index
        pageVisible = false
        pageLoader.y = window.pageGutter + 12
        pageLoader.scale = 0.985
        currentPage = pendingPage
        pendingPage = -1
        scroll.contentY = 0
    }

    function showFavoriteEditor() {
        if (currentPage === 3 && pageLoader.item && pageLoader.item.openNew)
            pageLoader.item.openNew()
    }

    function showQuickPanel() {
        quickPanel.reveal()
    }

    function toggleQuickPanel() {
        if (quickPanel.visible)
            quickPanel.hide()
        else
            quickPanel.reveal()
    }

    function hideQuickPanel() {
        quickPanel.hide()
    }

    onClosing: function(close) {
        if (wizz.shouldCloseToTray()) {
            close.accepted = false
            window.hide()
        }
    }

    onVisibilityChanged: {
        if (window.visibility === Window.Minimized) {
            if (window.startupMinimizing)
                window.startupMinimizing = false
            else if (wizz.shouldMinimizeToTray())
                Qt.callLater(function() { if (window.visibility === Window.Minimized) window.hide() })
        }
    }

            function showPage(index) {
        navigateTo(Math.max(0, Math.min(6, Number(index))))
    }

    QuickPanel { id: quickPanel; ownerWindow: window }
    Connections {
        target: wizz
        function onThemeChanged() {
            Theme.setMode(wizz.themeName)
            Theme.reduceMotion = wizz.reducedMotion
        }
        function onNavigateRequested(index) {
            window.show()
            window.raise()
            window.requestActivate()
            window.navigateTo(index)
            quickPanel.hide()
        }
        function onUpdateChanged() {
            if (wizz.updateCompletionNotice.length > 0) {
                window.updateToastVisible = true
                updateToastTimer.restart()
            }
        }
    }
    Timer { id: updateToastTimer; interval: 6500; onTriggered: window.updateToastVisible = false }
    Component.onCompleted: {
        Theme.setMode(wizz.themeName)
        Theme.reduceMotion = wizz.reducedMotion
    }

    Rectangle {
        objectName: "appShell"
        anchors.fill: parent
        radius: window.visibility === Window.Maximized ? 0 : 12
        color: Theme.bg
        border.width: 1
        border.color: Theme.stroke
        clip: true

        Rectangle {
            id: titleBar
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            height: 38
            color: Theme.surface
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 13; anchors.rightMargin: 9; spacing: 9
                Rectangle {
                    Layout.preferredWidth: 22; Layout.preferredHeight: 22; radius: 8; color: window.logoColor
                    Behavior on color { ColorAnimation { duration: Theme.reduceMotion ? 0 : 130; easing.type: Easing.InOutSine } }
                    BulbIcon { anchors.centerIn: parent; width: 15; height: 15; iconColor: "white" }
                }
                Text { text: "WizZ Desktop"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.DemiBold }
                Item { Layout.fillWidth: true }
                Rectangle {
                    Layout.preferredWidth: 42; Layout.preferredHeight: 30; radius: 8; color: minMouse.containsMouse ? Theme.cardHi : "transparent"
                    AppIcon { anchors.centerIn: parent; width: 12; height: 12; name: "minimize"; color: Theme.muted }
                    MouseArea {
                        id: minMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (wizz.shouldMinimizeToTray()) window.hide()
                            else window.showMinimized()
                        }
                    }
                }
                Rectangle {
                    Layout.preferredWidth: 42; Layout.preferredHeight: 30; radius: 8; color: closeMouse.containsMouse ? "#8f2637" : "transparent"
                    AppIcon { anchors.centerIn: parent; width: 14; height: 14; name: "close"; color: closeMouse.containsMouse ? "white" : Theme.muted }
                    MouseArea { id: closeMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: window.close() }
                }
            }
            DragHandler { onActiveChanged: if (active) window.startSystemMove() }
        }

        Rectangle {
            id: sidebar
            anchors.left: parent.left; anchors.top: titleBar.bottom; anchors.bottom: parent.bottom
            width: window.width < 960 ? 86 : 98
            color: Theme.surface
            Behavior on width { NumberAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } }
            Column {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top; anchors.topMargin: window.compactHeight ? 12 : 18
                spacing: window.compactHeight ? 4 : 12
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 52; height: 52; radius: 17
                    color: Qt.rgba(window.logoColor.r, window.logoColor.g, window.logoColor.b, 0.18)
                    border.width: 1
                    border.color: window.logoColor
                    Behavior on color { ColorAnimation { duration: Theme.reduceMotion ? 0 : 130; easing.type: Easing.InOutSine } }
                    Behavior on border.color { ColorAnimation { duration: Theme.reduceMotion ? 0 : 130; easing.type: Easing.InOutSine } }
                    BulbIcon { anchors.centerIn: parent; width: 30; height: 30; iconColor: window.logoColor
                        Behavior on iconColor { ColorAnimation { duration: Theme.reduceMotion ? 0 : 130; easing.type: Easing.InOutSine } }
                    }
                }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "WizZ"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.Bold }
                Repeater {
                    model: window.navigationItems
                    delegate: NavButton {
                        required property int index
                        required property var modelData
                        title: modelData.title; iconName: modelData.icon; selected: index === window.currentPage
                        compact: window.compactHeight
                        opacity: selected || index === 0 ? 1 : 0.72
                        Behavior on opacity { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                        onClicked: window.navigateTo(index)
                    }
                }
            }
        }

        Item {
            id: contentArea
            anchors.left: sidebar.right; anchors.right: parent.right
            anchors.top: titleBar.bottom; anchors.bottom: parent.bottom

            Rectangle { anchors.fill: parent; color: Theme.bg }

            Flickable {
                id: scroll
                objectName: "pageScroll"
                anchors.fill: parent
                contentWidth: width
                readonly property real pageWidth: Math.min(width - window.pageGutter * 2, window.contentMaxWidth)
                contentHeight: window.currentPage === 0
                    ? homeColumn.y + homeColumn.height + window.pageGutter
                    : pageLoader.y + pageLoader.height + window.pageGutter
                clip: true
                interactive: true
                acceptedButtons: Qt.NoButton
                flickableDirection: Flickable.VerticalFlick
                boundsBehavior: Flickable.StopAtBounds
                flickDeceleration: 11500
                maximumFlickVelocity: 4200
                pixelAligned: true
                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                    interactive: true
                    width: 7
                    contentItem: Rectangle { radius: 4; color: Qt.rgba(Theme.muted.r, Theme.muted.g, Theme.muted.b, 0.42) }
                    background: Item {}
                }

                Column {
                    id: homeColumn
                    x: (scroll.width - scroll.pageWidth) / 2; y: window.pageGutter
                    width: scroll.pageWidth
                    spacing: 16
                    visible: window.currentPage === 0

                    RowLayout {
                        width: parent.width
                        ColumnLayout {
                            spacing: 2
                            Text { text: wizz.language === "en" ? "Home" : "Inicio"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: Theme.pageTitleSize; font.weight: Theme.pageTitleWeight }
                            Text { text: wizz.language === "en" ? "Main lighting control" : "Control principal de iluminación"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.bodySize }
                        }
                        Item { Layout.fillWidth: true }
                        PressSurface {
                            Layout.preferredWidth: 236; implicitHeight: 54; radius: 18; accentColor: Theme.success
                            onClicked: quickPanel.visible ? quickPanel.hide() : quickPanel.reveal()
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 14; spacing: 10
                                Rectangle { Layout.preferredWidth: 8; Layout.preferredHeight: 8; radius: 4; color: Theme.success }
                                ColumnLayout {
                                     Layout.fillWidth: true
                                    spacing: 0
                                     Text { Layout.fillWidth: true; text: wizz.statusLine; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold; elide: Text.ElideRight }
                                     Text { Layout.fillWidth: true; text: wizz.targetLine; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; elide: Text.ElideRight }
                                }
                                AppIcon { Layout.preferredWidth: 16; Layout.preferredHeight: 16; name: "arrowRight"; color: Theme.muted }
                            }
                        }
                    }

                    RowLayout {
                        width: parent.width
                        Text { text: wizz.language === "en" ? "LINKED LIGHTS" : "LUCES VINCULADAS"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 15; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        Text { text: wizz.language === "en" ? wizz.selectedCount + " of " + wizz.totalCount + " selected" : wizz.selectedCount + " de " + wizz.totalCount + " seleccionadas"; color: Theme.accent; font.family: Theme.uiFont; font.pixelSize: 12 }
                        PressSurface {
                            Layout.preferredWidth: 64; Layout.preferredHeight: 30; radius: 15
                            color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.primary
                            onClicked: wizz.selectAll()
                            Text { anchors.centerIn: parent; text: wizz.language === "en" ? "All" : "Todas"; color: Theme.accent; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                        }
                    }

                    GridLayout {
                        id: lightsGrid
                        width: parent.width
                        columns: width >= 820 ? 3 : 2
                        columnSpacing: 12; rowSpacing: 12
                        Repeater {
                            model: wizz.lightModel
                            delegate: LightCard {
                                Layout.fillWidth: true
                                onClicked: wizz.toggleLight(address)
                            }
                        }
                    }

                    PressSurface {
                        width: parent.width
                        implicitHeight: 116
                        accentColor: Theme.primary
                        selected: wizz.powerOn
                        onClicked: wizz.toggleMaster()
                        RowLayout {
                            anchors.fill: parent; anchors.margins: 20; spacing: 18
                            Rectangle {
                                Layout.preferredWidth: 70; Layout.preferredHeight: 70; radius: 23
                                color: wizz.powerOn ? Theme.primary : Theme.cardHi
                                Item {
                                    anchors.centerIn: parent; width: 30; height: 30
                                    AppIcon { anchors.fill: parent; name: "power"; color: Theme.text; strokeWidth: 2 }
                                }
                            }
                            ColumnLayout {
                                spacing: 2
                                Text { text: wizz.language === "en" ? "Master control" : "Control maestro"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.bodySize }
                                Text { text: wizz.powerOn ? (wizz.language === "en" ? "ON" : "ENCENDIDO") : (wizz.language === "en" ? "OFF" : "APAGADO"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 19; font.weight: Theme.stateWeight }
                                Text { text: wizz.language === "en" ? "Click to toggle the active target" : "Toca para alternar el target activo"; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize }
                            }
                            Item { Layout.fillWidth: true }
                            AppIcon { Layout.preferredWidth: 22; Layout.preferredHeight: 22; name: "arrowRight"; color: Theme.accent }
                        }
                    }

                    Rectangle {
                        width: parent.width; height: 112; radius: Theme.radiusMedium
                        color: Theme.card; border.width: 1; border.color: Theme.stroke
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 18; spacing: 7
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: wizz.language === "en" ? "BRIGHTNESS" : "BRILLO"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                                Item { Layout.fillWidth: true }
                                Text { text: Math.round(mainSlider.value) + "%"; color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 13; font.weight: Font.Bold }
                            }
                            Slider {
                                id: mainSlider
                                Layout.fillWidth: true
                                from: 10; to: 100; value: wizz.brightness
                                onMoved: wizz.queueBrightness(Math.round(value))
                                background: Rectangle {
                                    x: mainSlider.leftPadding; y: mainSlider.topPadding + mainSlider.availableHeight / 2 - height / 2
                                    width: mainSlider.availableWidth; height: 5; radius: 3; color: Theme.stroke
                                    Rectangle { width: mainSlider.visualPosition * parent.width; height: parent.height; radius: parent.radius; color: Theme.primary }
                                }
                                handle: Rectangle {
                                    x: mainSlider.leftPadding + mainSlider.visualPosition * (mainSlider.availableWidth - width)
                                    y: mainSlider.topPadding + mainSlider.availableHeight / 2 - height / 2
                                    width: 20; height: 20; radius: 10; color: Theme.text
                                }
                            }
                        }
                    }

                    RowLayout {
                        width: parent.width
                        Text { text: wizz.language === "en" ? "QUICK ACTIONS" : "ACCESOS RÁPIDOS"; color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        PressSurface {
                            Layout.preferredWidth: 112; Layout.preferredHeight: 30; radius: 15
                            color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.primary
                            onClicked: window.navigateTo(5)
                            Text { anchors.centerIn: parent; text: wizz.language === "en" ? "Manage →" : "Administrar →"; color: Theme.primary; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                        }
                    }
                    Text { visible: wizz.quickActions.length === 0; text: wizz.language === "en" ? "No quick actions selected. Add them in Settings." : "No hay acciones rápidas visibles. Agrégalas en Ajustes."; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.labelSize }
                    GridLayout {
                        width: parent.width
                        columns: width >= 1080 ? 8 : width >= 700 ? 4 : 2
                        columnSpacing: 10
                        Repeater {
                            model: wizz.quickActions
                            delegate: QuickAction {
                                required property var modelData
                                Layout.fillWidth: true
                                title: modelData.title; glyph: modelData.glyph; actionColor: modelData.color
                                onClicked: wizz.applyQuick(modelData.key)
                            }
                        }
                    }
                    RowLayout {
                        width: parent.width
                    Text { text: wizz.language === "en" ? "FAVORITES" : "FAVORITOS"; color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                        Item { Layout.fillWidth: true }
                        PressSurface {
                            Layout.preferredWidth: 112; Layout.preferredHeight: 30; radius: 15
                            color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.primary
                            onClicked: window.navigateTo(3)
                            Text { anchors.centerIn: parent; text: wizz.language === "en" ? "Manage →" : "Administrar →"; color: Theme.primary; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                        }
                    }
                    GridLayout {
                        width: parent.width; columns: width >= 820 ? 3 : 2; columnSpacing: 10; rowSpacing: 10
                        Repeater {
                            model: wizz.favoriteModel
                            delegate: PressSurface {
                                required property string title
                                required property string subtitle
                                required property color entryColor
                                required property string uid
                                Layout.fillWidth: true; implicitHeight: 56; radius: 14; accentColor: entryColor
                                onClicked: wizz.applyFavorite(uid)
                                RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 11
                                    Rectangle { Layout.preferredWidth: 22; Layout.preferredHeight: 22; radius: 11; color: entryColor }
                                    ColumnLayout { Layout.fillWidth: true; spacing: 1; Text { Layout.fillWidth: true; text: title; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold; elide: Text.ElideRight } Text { Layout.fillWidth: true; text: subtitle; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; elide: Text.ElideRight } }
                                }
                            }
                        }
                    }
                }

                Loader {
                    id: pageLoader
                    x: (scroll.width - scroll.pageWidth) / 2; y: window.pageGutter
                    width: scroll.pageWidth
                    height: item ? item.implicitHeight : 0
                    active: window.currentPage !== 0
                    opacity: window.pageVisible ? 1 : 0
                    scale: window.pageVisible ? 1 : 0.985
                    Behavior on opacity { NumberAnimation { duration: window.pageVisible ? Theme.motionPage : 0; easing.type: Easing.OutCubic } }
                    Behavior on y { NumberAnimation { duration: Theme.motionPage; easing.type: Easing.OutCubic } }
                    Behavior on scale { NumberAnimation { duration: Theme.motionPage; easing.type: Easing.OutCubic } }
                    onLoaded: revealPage.restart()
                    Timer { id: revealPage; interval: 16; onTriggered: { window.pageVisible = true; pageLoader.opacity = 1; pageLoader.y = window.pageGutter; pageLoader.scale = 1 } }
                    sourceComponent: window.currentPage === 1 ? colorPage : window.currentPage === 2 ? scenesPage : window.currentPage === 3 ? favoritesPage : window.currentPage === 4 ? routinesPage : window.currentPage === 5 ? settingsPage : hotkeysPage
                }
            }
        }
    }

    Rectangle {
        id: updatePreparationOverlay
        z: 990
        anchors.fill: parent
        visible: wizz.updatePreparing
        color: "#B8000612"

        MouseArea { anchors.fill: parent }

        Rectangle {
            anchors.centerIn: parent
            width: Math.min(parent.width - 40, 470)
            height: 208
            radius: 20
            color: Theme.cardHi
            border.width: 1
            border.color: Theme.stroke

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 26
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    text: wizz.language === "es" ? "Actualizando WizZ Desktop" : "Updating WizZ Desktop"
                    color: Theme.text
                    font.family: Theme.controlFont
                    font.pixelSize: 20
                    font.weight: Font.Bold
                }
                Text {
                    Layout.fillWidth: true
                    text: wizz.updateStatus
                    color: Theme.muted
                    font.family: Theme.uiFont
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 9
                    radius: 5
                    color: Theme.stroke
                    Rectangle {
                        width: parent.width * Math.max(0, Math.min(100, wizz.updateProgress)) / 100
                        height: parent.height
                        radius: 5
                        color: Theme.primary
                        Behavior on width { NumberAnimation { duration: Theme.motionNormal; easing.type: Easing.OutCubic } }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: (wizz.language === "es" ? "Preparación: " : "Preparation: ") + wizz.updateProgress + "%"
                    horizontalAlignment: Text.AlignRight
                    color: Theme.primary
                    font.family: Theme.controlFont
                    font.pixelSize: 13
                    font.weight: Font.Bold
                }
                Text {
                    Layout.fillWidth: true
                    text: wizz.language === "es"
                          ? "Al cerrar la app, una ventana pequeña mostrará la instalación y el reinicio."
                          : "After the app closes, a small window will show installation and restart progress."
                    color: Theme.faint
                    font.family: Theme.uiFont
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    Rectangle {
        id: updateToast
        z: 1000
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: window.updateToastVisible ? 22 : 8
        width: Math.min(parent.width - 36, 520)
        height: 58
        radius: 16
        visible: opacity > 0
        opacity: window.updateToastVisible ? 1 : 0
        color: Theme.cardHi
        border.width: 1
        border.color: wizz.updateCompletionNotice.indexOf("failed") >= 0 || wizz.updateCompletionNotice.indexOf("could not") >= 0 || wizz.updateCompletionNotice.indexOf("pudo") >= 0 ? Theme.warning : Theme.success
        Behavior on opacity { NumberAnimation { duration: Theme.motionNormal; easing.type: Easing.OutCubic } }
        Behavior on anchors.bottomMargin { NumberAnimation { duration: Theme.motionNormal; easing.type: Easing.OutCubic } }
        RowLayout {
            anchors.fill: parent; anchors.margins: 14; spacing: 10
            AppIcon {
                Layout.preferredWidth: 18; Layout.preferredHeight: 18
                name: updateToast.border.color === Theme.warning ? "info" : "check"
                color: updateToast.border.color
            }
            Text {
                Layout.fillWidth: true
                text: wizz.updateCompletionNotice
                color: Theme.text; font.family: Theme.uiFont; font.pixelSize: 12; font.weight: Font.DemiBold
                wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight
            }
        }
    }

    Component { id: colorPage; ColorPage {} }
    Component { id: scenesPage; ScenesPage { openEditorOnLoad: window.qaOpenSceneEditor } }
    Component { id: favoritesPage; FavoritesPage { openEditorOnLoad: window.qaOpenFavoriteEditor; qaEditorKind: window.qaFavoriteEditorKind } }
    Component { id: routinesPage; RoutinesPage { openEditorOnLoad: window.qaOpenRoutineEditor; openScheduleEditorOnLoad: window.qaOpenScheduleEditor; openScheduleTargetOnLoad: window.qaOpenScheduleTarget } }
    Component { id: settingsPage; SettingsPage {} }
    Component { id: hotkeysPage; HotkeysPage {} }
}
