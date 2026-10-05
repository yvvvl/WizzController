pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    implicitHeight: settingsContent.implicitHeight
    property string editingIp: ""
    property string deletingIp: ""
    property string deletingName: ""
    property var selectedInfo: ({})

    function t(spanish, english) { return wizz.language === "en" ? english : spanish }

    function openRename(ip, name) {
        editingIp = ip
        renameField.text = name
        renameDialog.open()
    }

    function openInfo(ip) {
        selectedInfo = wizz.deviceInfo(ip)
        infoDialog.open()
    }

    ColumnLayout {
        id: settingsContent
        width: parent.width
        spacing: 16

        RowLayout {
            Layout.fillWidth: true; spacing: 10
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                Text { text: root.t("Ajustes", "Settings"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: Theme.pageTitleSize; font.weight: Font.Bold }
                Text { text: root.t("Destino, búsqueda y comportamiento de WizZ Desktop", "Target, discovery, and WizZ Desktop behavior"); color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.bodySize }
            }
            PressSurface {
                Layout.preferredWidth: 122; Layout.preferredHeight: 38; radius: 19
                color: "transparent"; outlined: true; border.color: Theme.stroke
                onClicked: addDialog.open()
                Text { anchors.centerIn: parent; text: "+  " + root.t("Agregar IP", "Add IP"); color: Theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
            }
            PressSurface {
                Layout.preferredWidth: 156; Layout.preferredHeight: 38; radius: 19
                color: Theme.primary; accentColor: Theme.primary
                onClicked: wizz.scanLights()
                Text { anchors.centerIn: parent; text: wizz.scanInProgress ? root.t("Buscando…", "Searching…") : root.t("Buscar luces", "Find lights"); color: "white"; font.pixelSize: 12; font.weight: Font.Bold }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 54
            visible: wizz.scanInProgress
            radius: 14; color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.10)
            border.width: 1; border.color: Theme.stroke
            RowLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 10
                Rectangle { Layout.preferredWidth: 9; Layout.preferredHeight: 9; radius: 5; color: Theme.success }
                Text { Layout.fillWidth: true; text: wizz.scanMessage; color: Theme.muted; font.pixelSize: Theme.labelSize }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: targetContent.implicitHeight + 36
            radius: Theme.radiusMedium; color: Theme.card; border.width: 1; border.color: Theme.stroke
            ColumnLayout {
                id: targetContent
                anchors.fill: parent; anchors.margins: 18; spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: root.t("DESTINO", "TARGET"); color: Theme.muted; font.pixelSize: Theme.labelSize; font.weight: Font.Bold; font.letterSpacing: 0.7 }
                    Item { Layout.fillWidth: true }
                    Text { text: wizz.language === "en" ? wizz.selectedCount + " selected" : wizz.selectedCount + " seleccionada" + (wizz.selectedCount === 1 ? "" : "s"); color: Theme.accent; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    Rectangle { Layout.preferredWidth: 42; Layout.preferredHeight: 42; radius: 13; color: Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.16); AppIcon { anchors.centerIn: parent; width: 18; height: 18; name: "target"; color: Theme.warning } }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { text: wizz.targetLine; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                        Text { text: root.t("Selecciona una o varias tarjetas para dirigir los comandos.", "Select one or more cards to direct commands."); color: Theme.faint; font.pixelSize: Theme.captionSize }
                    }
                    PressSurface { Layout.preferredWidth: 112; Layout.preferredHeight: 34; radius: 17; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: wizz.selectAll(); Text { anchors.centerIn: parent; text: root.t("Seleccionar todo", "Select all"); color: Theme.text; font.pixelSize: Theme.captionSize } }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    PressSurface {
                        Layout.preferredWidth: 104; Layout.preferredHeight: 30; radius: 15
                        selected: wizz.targetMode === "single"; accentColor: Theme.primary
                        onClicked: wizz.setTargetMode("single")
                        Text { anchors.centerIn: parent; text: root.t("Selección", "Selection"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                    }
                    PressSurface {
                        Layout.preferredWidth: 86; Layout.preferredHeight: 30; radius: 15
                        selected: wizz.targetMode === "all"; accentColor: Theme.primary
                        onClicked: wizz.setTargetMode("all")
                        Text { anchors.centerIn: parent; text: root.t("Todas", "All"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold }
                    }
                    Item { Layout.fillWidth: true }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke }
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    ColumnLayout { Layout.fillWidth: true; spacing: 3; Text { text: root.t("RESPUESTA DE CONTROLES", "CONTROL RESPONSE"); color: Theme.muted; font.pixelSize: Theme.captionSize; font.weight: Font.Bold } Text { Layout.fillWidth: true; text: root.t("Equilibra continuidad visual y tráfico de red.", "Balance visual continuity and network traffic."); color: Theme.muted; font.pixelSize: Theme.captionSize; wrapMode: Text.WordWrap } }
                    WizComboBox {
                        id: intervalBox
                        Layout.preferredWidth: 218; Layout.preferredHeight: 42
                        model: wizz.language === "en"
                            ? ["35 ms · fastest", "65 ms · recommended", "90 ms · stable", "130 ms · conservative"]
                            : ["35 ms · máxima", "65 ms · recomendada", "90 ms · estable", "130 ms · conservadora"]
                        currentIndex: wizz.sliderInterval <= 35 ? 0 : wizz.sliderInterval <= 65 ? 1 : wizz.sliderInterval <= 90 ? 2 : 3
                        onActivated: wizz.setSliderInterval([35, 65, 90, 130][currentIndex])
                        contentItem: Text { leftPadding: 13; text: intervalBox.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: Theme.labelSize }
                        background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: intervalBox.activeFocus ? Theme.primary : Theme.stroke }
                    }
                    PressSurface { Layout.preferredWidth: 128; Layout.preferredHeight: 38; radius: 19; color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.error; onClicked: wizz.cleanupOfflineLights(); Text { anchors.centerIn: parent; text: root.t("Limpiar desconectadas", "Remove offline"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.DemiBold } }
                }
            }
        }

        QuickActionsEditor { Layout.fillWidth: true }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: appearanceContent.implicitHeight + 36
            radius: Theme.radiusMedium; color: Theme.card; border.width: 1; border.color: Theme.stroke
            ColumnLayout {
                id: appearanceContent
                anchors.fill: parent; anchors.margins: 18; spacing: 12
                Text { text: root.t("APARIENCIA", "APPEARANCE"); color: Theme.muted; font.pixelSize: Theme.labelSize; font.weight: Font.Bold; font.letterSpacing: 0.7 }
                Text { text: root.t("Elige un estilo; todos los componentes comparten los mismos colores.", "Choose a style; every component shares the same colors."); color: Theme.faint; font.pixelSize: Theme.captionSize }
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { text: wizz.language === "en" ? "Application language" : "Idioma de la aplicación"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                        Text { text: wizz.language === "en" ? "Choose the language used across the application." : "Elige el idioma que se usa en toda la aplicación."; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize }
                    }
                    WizComboBox {
                        id: languageBox; Layout.preferredWidth: 150; Layout.preferredHeight: 40
                        model: ["English", "Español"]
                        currentIndex: wizz.language === "es" ? 1 : 0
                        onActivated: wizz.setLanguage(currentIndex === 1 ? "es" : "en")
                        contentItem: Text { leftPadding: 13; text: languageBox.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: Theme.labelSize }
                        background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: languageBox.activeFocus ? Theme.primary : Theme.stroke }
                    }
                }
                GridLayout {
                    id: themeGrid
                    // Eight distinct surfaces cover the useful visual moods
                    // without presenting near-duplicate blues as a wall of
                    // cards.  Four equal columns make the chooser symmetric.
                    Layout.fillWidth: true; columns: width >= 780 ? 4 : width >= 520 ? 2 : 1; columnSpacing: 10; rowSpacing: 10
                    Repeater {
                        id: themeChoices
                        model: [
                            {name:"midnight",label:root.t("Medianoche", "Midnight"),color:"#6697ff"},{name:"ocean",label:root.t("Océano", "Ocean"),color:"#42c5dc"},
                            {name:"violet",label:root.t("Violeta", "Violet"),color:"#a577ff"},{name:"forest",label:root.t("Bosque", "Forest"),color:"#58d69a"},
                            {name:"ember",label:root.t("Ámbar", "Amber"),color:"#ff8663"},{name:"rose",label:root.t("Rosa", "Rose"),color:"#fa72bb"},
                            {name:"coral",label:root.t("Coral", "Coral"),color:"#ff7b8b"},{name:"lime",label:root.t("Lima", "Lime"),color:"#9de85b"},
                            {name:"cobalt",label:root.t("Cobalto", "Cobalt"),color:"#5f8fff"},{name:"sunset",label:root.t("Atardecer", "Sunset"),color:"#ff9d5c"},
                            {name:"oled",label:"OLED",color:"#10121a"},{name:"light",label:root.t("Claro", "Light"),color:"#f6f8fc"}
                        ]
                        delegate: PressSurface {
                            id: themeCard
                            required property int index
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 58; radius: 12
                            accentColor: themeCard.modelData.color; selected: wizz.themeName === themeCard.modelData.name
                            onClicked: wizz.setTheme(themeCard.modelData.name)
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 12; spacing: 9
                                Rectangle { Layout.preferredWidth: 24; Layout.preferredHeight: 24; radius: 8; color: themeCard.modelData.color; border.width: themeCard.modelData.name === "light" ? 1 : 0; border.color: Theme.stroke }
                                Text { Layout.fillWidth: true; text: themeCard.modelData.label; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                                AppIcon { visible: themeCard.selected; Layout.preferredWidth: 13; Layout.preferredHeight: 13; name: "check"; color: Theme.primary }
                            }
                        }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 62; radius: 13
                    color: Theme.cardHi; border.width: 1; border.color: Theme.stroke
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 13; spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Text { text: root.t("Reducir animaciones", "Reduce animations"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                            Text { text: root.t("Elimina transiciones no esenciales y mantiene la respuesta inmediata.", "Removes non-essential transitions and keeps the response immediate."); color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize }
                        }
                        PressSurface {
                            Layout.preferredWidth: 48; Layout.preferredHeight: 28; radius: 14
                            color: wizz.reducedMotion ? Theme.primary : Theme.stroke
                            accentColor: Theme.primary
                            onClicked: wizz.setReducedMotion(!wizz.reducedMotion)
                            Rectangle {
                                width: 20; height: 20; radius: 10
                                anchors.verticalCenter: parent.verticalCenter
                                x: wizz.reducedMotion ? parent.width - width - 4 : 4
                                color: Theme.text
                                Behavior on x { NumberAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } }
                            }
                        }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 62; radius: 13
                    color: Theme.cardHi; border.width: 1; border.color: Theme.stroke
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 13; spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Text { text: root.t("Icono con color de las luces", "Light-colored icon"); color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                            Text { text: root.t("Tiñe sólo el icono WiZ con el estado actual; desactívalo para usar el color del tema.", "Tints only the WiZ icon with the current state; turn it off to use the theme color."); color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize }
                        }
                        PressSurface {
                            Layout.preferredWidth: 48; Layout.preferredHeight: 28; radius: 14
                            color: wizz.liveBrandAccent ? Theme.primary : Theme.stroke; accentColor: Theme.primary
                            onClicked: wizz.setLiveBrandAccent(!wizz.liveBrandAccent)
                            Rectangle { width: 20; height: 20; radius: 10; anchors.verticalCenter: parent.verticalCenter; x: wizz.liveBrandAccent ? parent.width - width - 4 : 4; color: Theme.text; Behavior on x { NumberAnimation { duration: Theme.motionFast; easing.type: Easing.OutCubic } } }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: wizz.updateInProgress ? 112 : 86; radius: Theme.radiusMedium
            color: Theme.card; border.width: 1; border.color: Theme.stroke
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16; anchors.topMargin: 12; anchors.bottomMargin: 12; spacing: 14
                Rectangle { Layout.preferredWidth: 46; Layout.preferredHeight: 46; radius: 14; color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.16); BulbIcon { anchors.centerIn: parent; width: 25; height: 25; iconColor: Theme.primary } }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 3
                    Text { text: wizz.appProduct + " · " + wizz.appVersion; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 13; font.weight: Font.Bold }
                    Text { Layout.fillWidth: true; text: wizz.updateStatus; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: Theme.captionSize; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight }
                    ProgressBar {
                        id: updateProgress
                        visible: wizz.updateInProgress
                        Layout.fillWidth: true; Layout.preferredHeight: 5
                        from: 0; to: 100; value: wizz.updateProgress
                        indeterminate: !wizz.updatePreparing
                        background: Rectangle { implicitHeight: 5; radius: 3; color: Theme.stroke }
                        contentItem: Item {
                            id: updateProgressContent
                            property real sweepWidth: Math.max(32, width * 0.28)
                            property real sweepX: -sweepWidth
                            Rectangle {
                                id: updateSweep
                                width: updateProgress.indeterminate ? parent.sweepWidth : updateProgress.visualPosition * parent.width
                                x: updateProgress.indeterminate ? parent.sweepX : 0
                                height: parent.height; radius: 3; color: Theme.primary
                                Behavior on width { NumberAnimation { duration: Theme.motionNormal; easing.type: Easing.OutCubic } }
                            }
                            SequentialAnimation on sweepX {
                                    running: updateProgress.indeterminate
                                    loops: Animation.Infinite
                                    NumberAnimation { from: -updateProgressContent.sweepWidth; to: updateProgress.width; duration: 1050; easing.type: Easing.InOutCubic }
                            }
                        }
                    }
                }
                RowLayout {
                    spacing: 8
                    PressSurface {
                        Layout.preferredWidth: 142; Layout.preferredHeight: 34; radius: 17
                        visible: !wizz.updatePreparing
                        color: "transparent"; outlined: true; border.color: Theme.stroke
                        accentColor: Theme.primary; enabled: !wizz.updateInProgress
                        onClicked: wizz.checkUpdates()
                        Text {
                            anchors.centerIn: parent
                            text: wizz.updateInProgress ? root.t("Buscando…", "Checking…") : root.t("Buscar actualización", "Check for updates")
                            color: Theme.text; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold
                        }
                    }
                    PressSurface {
                        Layout.preferredWidth: 142; Layout.preferredHeight: 34; radius: 17
                        visible: wizz.updateAvailable || wizz.updatePreparing
                        color: Theme.primary; accentColor: Theme.primary
                        enabled: !wizz.updateInProgress
                        onClicked: { if (wizz.updateCanInstall) wizz.installUpdate(); else Qt.openUrlExternally(wizz.updateUrl) }
                        Text {
                            anchors.centerIn: parent
                            text: wizz.updatePreparing
                                ? root.t("Actualizando · ", "Updating · ") + wizz.updateProgress + "%"
                                : wizz.updateCanInstall ? root.t("Instalar y reiniciar", "Install and restart") : root.t("Abrir descarga", "Open download")
                            color: "white"; font.family: Theme.controlFont; font.pixelSize: Theme.captionSize; font.weight: Font.Bold
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text { text: root.t("AMPOLLETAS", "LIGHTS"); color: Theme.muted; font.pixelSize: Theme.labelSize; font.weight: Font.Bold; font.letterSpacing: 0.7 }
            Item { Layout.fillWidth: true }
            Text { text: wizz.scanMessage; color: Theme.faint; font.pixelSize: Theme.captionSize }
        }
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 66; visible: wizz.totalCount === 0
            radius: 14; color: Theme.card; border.width: 1; border.color: Theme.stroke
            Text { anchors.centerIn: parent; text: root.t("No hay ampolletas vinculadas. Usa Buscar luces o agrega una IP.", "No linked lights. Use Find lights or add an IP."); color: Theme.muted; font.pixelSize: Theme.labelSize }
        }
        GridLayout {
            Layout.fillWidth: true; columns: width >= 740 ? 2 : 1; columnSpacing: 12; rowSpacing: 12
            Repeater {
                model: wizz.lightModel
                delegate: PressSurface {
                    id: deviceCard
                    required property string displayName
                    required property string address
                    required property bool isOnline
                    required property bool isSelected
                    required property string moduleName
                    Layout.fillWidth: true; Layout.preferredHeight: 104
                    // A selected device is part of the current workspace,
                    // so it follows the active theme rather than staying
                    // permanently green in every palette.
                    accentColor: isSelected ? Theme.primary : isOnline ? Theme.success : Theme.error; selected: isSelected
                    onClicked: wizz.toggleLight(address)
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 14; spacing: 12
                        Rectangle { Layout.preferredWidth: 44; Layout.preferredHeight: 44; radius: 14; color: Qt.rgba(deviceCard.accentColor.r, deviceCard.accentColor.g, deviceCard.accentColor.b, 0.16); AppIcon { anchors.centerIn: parent; width: 17; height: 17; name: "bulb"; color: deviceCard.accentColor } }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Text { Layout.fillWidth: true; text: deviceCard.displayName; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight }
                            Text { text: deviceCard.address; color: Theme.muted; font.pixelSize: Theme.labelSize }
                            Text { Layout.fillWidth: true; text: (deviceCard.isOnline ? "En línea" : "Sin respuesta") + (deviceCard.moduleName ? " · " + deviceCard.moduleName : ""); color: Theme.faint; font.pixelSize: Theme.captionSize; elide: Text.ElideRight }
                        }
                        Rectangle { Layout.preferredWidth: 9; Layout.preferredHeight: 9; radius: 5; color: deviceCard.isSelected ? Theme.primary : Theme.stroke }
                        PressSurface {
                            Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17
                            color: deviceCard.address === wizz.activeLightIp ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.18) : "transparent"
                            accentColor: Theme.primary
                            onClicked: wizz.setActiveLight(deviceCard.address)
                            AppIcon { anchors.centerIn: parent; width: 16; height: 16; name: "target"; color: Theme.primary }
                        }
                        PressSurface {
                            Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17
                            color: "transparent"; accentColor: Theme.primary
                            onClicked: root.openInfo(deviceCard.address)
                            AppIcon { anchors.centerIn: parent; width: 15; height: 15; name: "info"; color: Theme.muted }
                        }
                        PressSurface { Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17; color: "transparent"; border.width: 0; onClicked: root.openRename(deviceCard.address, deviceCard.displayName); AppIcon { anchors.centerIn: parent; width: 14; height: 14; name: "edit"; color: Theme.primary } }
                        PressSurface { Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17; color: "transparent"; border.width: 0; accentColor: Theme.error; onClicked: { root.deletingIp = deviceCard.address; root.deletingName = deviceCard.displayName; deleteDialog.open() } AppIcon { anchors.centerIn: parent; width: 13; height: 13; name: "close"; color: Theme.error } }
                    }
                }
            }
        }
    }

    Popup {
        id: infoDialog
        parent: Overlay.overlay; anchors.centerIn: parent; width: Math.min(500, Overlay.overlay.width - 48); height: Math.min(510, Overlay.overlay.height - 48)
        modal: true; focus: true; dim: true; padding: 0; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 22; spacing: 12
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout { Layout.fillWidth: true; spacing: 2; Text { text: root.selectedInfo.name || root.t("Ampolleta WiZ", "WiZ light"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 21; font.weight: Font.Bold } Text { text: root.t("Información del dispositivo", "Device information"); color: Theme.muted; font.pixelSize: Theme.labelSize } }
                PressSurface { Layout.preferredWidth: 32; Layout.preferredHeight: 32; radius: 16; color: "transparent"; onClicked: infoDialog.close(); AppIcon { anchors.centerIn: parent; width: 14; height: 14; name: "close"; color: Theme.muted } }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke }
            GridLayout {
                Layout.fillWidth: true; columns: 2; columnSpacing: 12; rowSpacing: 8
                Repeater {
                    model: [
                        {label:"IP", value:root.selectedInfo.ip || "—"}, {label:"MAC", value:root.selectedInfo.mac || "—"},
                        {label:root.t("Estado", "Status"), value:root.selectedInfo.online ? root.t("En línea", "Online") : root.t("Sin respuesta", "No response")}, {label:root.t("Módulo", "Module"), value:root.selectedInfo.module || "—"},
                        {label:root.t("Brillo", "Brightness"), value:(root.selectedInfo.brightness || 0) + "%"}, {label:root.t("Temperatura", "Temperature"), value:root.selectedInfo.kelvin ? root.selectedInfo.kelvin + "K" : "—"},
                        {label:"RGB", value:root.selectedInfo.rgb ? root.t("Compatible", "Supported") : root.t("No disponible", "Unavailable")}, {label:root.t("Blancos", "Whites"), value:root.selectedInfo.tunableWhite ? root.t("Compatible", "Supported") : root.t("No disponible", "Unavailable")},
                        {label:root.t("Rango CCT", "CCT range"), value:root.selectedInfo.kelvinMin ? root.selectedInfo.kelvinMin + "–" + root.selectedInfo.kelvinMax + "K" : "—"}, {label:"Firmware", value:root.selectedInfo.firmware || "—"}
                    ]
                    delegate: Rectangle { required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 54; radius: 11; color: Theme.cardHi; border.width: 1; border.color: Theme.stroke; Column { anchors.fill: parent; anchors.margins: 10; spacing: 3; Text { text: modelData.label.toUpperCase(); color: Theme.faint; font.pixelSize: Theme.captionSize; font.weight: Font.Bold } Text { width: parent.width; text: modelData.value; color: Theme.text; font.pixelSize: Theme.labelSize; font.weight: Font.DemiBold; elide: Text.ElideRight } } }
                }
            }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                PressSurface {
                    Layout.preferredWidth: 132; Layout.preferredHeight: 38; radius: 19
                    color: Theme.primary; accentColor: Theme.primary
                    onClicked: {
                        wizz.setActiveLight(root.selectedInfo.ip || "")
                        infoDialog.close()
                    }
                    Text { anchors.centerIn: parent; text: root.t("Usar como activa", "Use as active"); color: "white"; font.family: Theme.controlFont; font.pixelSize: Theme.labelSize; font.weight: Font.Bold }
                }
            }
        }
    }

    Popup {
        id: addDialog
        parent: Overlay.overlay; anchors.centerIn: parent; width: Math.min(430, Overlay.overlay.width - 40); height: 238
        modal: true; focus: true; dim: true; padding: 0; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 22; spacing: 12
            Text { text: root.t("Agregar por IP", "Add by IP"); color: Theme.text; font.pixelSize: 21; font.weight: Font.Bold }
            Text { text: root.t("La ampolleta debe estar conectada a la misma red local.", "The light must be connected to the same local network."); color: Theme.muted; font.pixelSize: Theme.labelSize }
            TextField { id: ipField; Layout.fillWidth: true; Layout.preferredHeight: 44; placeholderText: "192.168.1.20"; color: Theme.text; placeholderTextColor: Theme.faint; leftPadding: 13; background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: ipField.activeFocus ? Theme.primary : Theme.stroke } }
            Item { Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } PressSurface { Layout.preferredWidth: 96; Layout.preferredHeight: 38; radius: 19; color: "transparent"; onClicked: addDialog.close(); Text { anchors.centerIn: parent; text: root.t("Cancelar", "Cancel"); color: Theme.text; font.pixelSize: Theme.labelSize } } PressSurface { Layout.preferredWidth: 106; Layout.preferredHeight: 38; radius: 19; color: Theme.primary; onClicked: { if (wizz.addLight(ipField.text)) { ipField.text = ""; addDialog.close() } } Text { anchors.centerIn: parent; text: root.t("Agregar", "Add"); color: "white"; font.pixelSize: Theme.labelSize; font.weight: Font.Bold } } }
        }
    }

    Popup {
        id: renameDialog
        parent: Overlay.overlay; anchors.centerIn: parent; width: Math.min(430, Overlay.overlay.width - 40); height: 220
        modal: true; focus: true; dim: true; padding: 0; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 22; spacing: 12
            Text { text: root.t("Renombrar ampolleta", "Rename light"); color: Theme.text; font.pixelSize: 21; font.weight: Font.Bold }
            TextField { id: renameField; Layout.fillWidth: true; Layout.preferredHeight: 44; color: Theme.text; leftPadding: 13; background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: renameField.activeFocus ? Theme.primary : Theme.stroke } }
            Item { Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } PressSurface { Layout.preferredWidth: 96; Layout.preferredHeight: 38; radius: 19; color: "transparent"; onClicked: renameDialog.close(); Text { anchors.centerIn: parent; text: root.t("Cancelar", "Cancel"); color: Theme.text; font.pixelSize: Theme.labelSize } } PressSurface { Layout.preferredWidth: 106; Layout.preferredHeight: 38; radius: 19; color: Theme.primary; onClicked: { if (wizz.renameLight(root.editingIp, renameField.text)) renameDialog.close() } Text { anchors.centerIn: parent; text: root.t("Guardar", "Save"); color: "white"; font.pixelSize: Theme.labelSize; font.weight: Font.Bold } } }
        }
    }

    Popup {
        id: deleteDialog
        parent: Overlay.overlay; anchors.centerIn: parent; width: Math.min(430, Overlay.overlay.width - 40); height: 215
        modal: true; focus: true; dim: true; padding: 0; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        Overlay.modal: Rectangle { color: "#99000000" }
        background: Rectangle { color: Theme.card; radius: 20; border.width: 1; border.color: Theme.stroke }
        contentItem: ColumnLayout {
            anchors.fill: parent; anchors.margins: 22; spacing: 10
            Text { text: root.t("Quitar ampolleta", "Remove light"); color: Theme.text; font.pixelSize: 21; font.weight: Font.Bold }
            Text { Layout.fillWidth: true; text: root.t("¿Quieres quitar “", "Do you want to remove “") + root.deletingName + root.t("”? Puedes recuperarla con una búsqueda posterior.", "”? You can find it again later."); color: Theme.muted; font.pixelSize: Theme.labelSize; wrapMode: Text.WordWrap }
            Item { Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } PressSurface { Layout.preferredWidth: 96; Layout.preferredHeight: 38; radius: 19; color: "transparent"; onClicked: deleteDialog.close(); Text { anchors.centerIn: parent; text: root.t("Cancelar", "Cancel"); color: Theme.text; font.pixelSize: Theme.labelSize } } PressSurface { Layout.preferredWidth: 106; Layout.preferredHeight: 38; radius: 19; color: Theme.error; accentColor: Theme.error; onClicked: { wizz.removeLight(root.deletingIp); deleteDialog.close() } Text { anchors.centerIn: parent; text: root.t("Quitar", "Remove"); color: "white"; font.pixelSize: Theme.labelSize; font.weight: Font.Bold } } }
        }
    }
}
