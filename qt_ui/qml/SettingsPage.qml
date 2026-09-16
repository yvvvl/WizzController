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
                Text { text: "Ajustes"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 30; font.weight: Font.Bold }
                Text { text: "Destino, discovery y comportamiento de WizZ Desktop"; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 13 }
            }
            PressSurface {
                Layout.preferredWidth: 122; Layout.preferredHeight: 38; radius: 19
                color: "transparent"; outlined: true; border.color: Theme.stroke
                onClicked: addDialog.open()
                Text { anchors.centerIn: parent; text: "+  Agregar IP"; color: Theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
            }
            PressSurface {
                Layout.preferredWidth: 156; Layout.preferredHeight: 38; radius: 19
                color: Theme.primary; accentColor: Theme.primary
                onClicked: wizz.scanLights()
                Text { anchors.centerIn: parent; text: wizz.scanInProgress ? "Buscando…" : "⌁  Buscar luces"; color: "white"; font.pixelSize: 12; font.weight: Font.Bold }
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
                Text { Layout.fillWidth: true; text: wizz.scanMessage; color: Theme.muted; font.pixelSize: 11 }
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
                    Text { text: "DESTINO"; color: Theme.muted; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 0.7 }
                    Item { Layout.fillWidth: true }
                    Text { text: wizz.selectedCount + " seleccionada" + (wizz.selectedCount === 1 ? "" : "s"); color: Theme.accent; font.pixelSize: 11; font.weight: Font.DemiBold }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    Rectangle { Layout.preferredWidth: 42; Layout.preferredHeight: 42; radius: 13; color: Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.16); Text { anchors.centerIn: parent; text: "◉"; color: Theme.warning; font.pixelSize: 18 } }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { text: wizz.targetLine; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold }
                        Text { text: "Selecciona una o varias tarjetas para dirigir los comandos."; color: Theme.faint; font.pixelSize: 10 }
                    }
                    PressSurface { Layout.preferredWidth: 112; Layout.preferredHeight: 34; radius: 17; color: "transparent"; outlined: true; border.color: Theme.stroke; onClicked: wizz.selectAll(); Text { anchors.centerIn: parent; text: "Seleccionar todo"; color: Theme.text; font.pixelSize: 10 } }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 8
                    PressSurface {
                        Layout.preferredWidth: 104; Layout.preferredHeight: 30; radius: 15
                        selected: wizz.targetMode === "single"; accentColor: Theme.primary
                        onClicked: wizz.setTargetMode("single")
                        Text { anchors.centerIn: parent; text: "Selección"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold }
                    }
                    PressSurface {
                        Layout.preferredWidth: 86; Layout.preferredHeight: 30; radius: 15
                        selected: wizz.targetMode === "all"; accentColor: Theme.primary
                        onClicked: wizz.setTargetMode("all")
                        Text { anchors.centerIn: parent; text: "Todas"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold }
                    }
                    Item { Layout.fillWidth: true }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke }
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    ColumnLayout { Layout.fillWidth: true; spacing: 3; Text { text: "RESPUESTA DE CONTROLES"; color: Theme.muted; font.pixelSize: 10; font.weight: Font.Bold } Text { text: "Equilibra continuidad visual y tráfico de red."; color: Theme.faint; font.pixelSize: 10 } }
                    WizComboBox {
                        id: intervalBox
                        Layout.preferredWidth: 218; Layout.preferredHeight: 42
                        model: ["35 ms · máxima", "65 ms · recomendada", "90 ms · estable", "130 ms · conservadora"]
                        currentIndex: wizz.sliderInterval <= 35 ? 0 : wizz.sliderInterval <= 65 ? 1 : wizz.sliderInterval <= 90 ? 2 : 3
                        onActivated: wizz.setSliderInterval([35, 65, 90, 130][currentIndex])
                        contentItem: Text { leftPadding: 13; text: intervalBox.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 11 }
                        background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: intervalBox.activeFocus ? Theme.primary : Theme.stroke }
                    }
                    PressSurface { Layout.preferredWidth: 112; Layout.preferredHeight: 38; radius: 19; color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.error; onClicked: wizz.cleanupOfflineLights(); Text { anchors.centerIn: parent; text: "Limpiar offline"; color: Theme.text; font.pixelSize: 10; font.weight: Font.DemiBold } }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: appearanceContent.implicitHeight + 36
            radius: Theme.radiusMedium; color: Theme.card; border.width: 1; border.color: Theme.stroke
            ColumnLayout {
                id: appearanceContent
                anchors.fill: parent; anchors.margins: 18; spacing: 12
                Text { text: "APARIENCIA"; color: Theme.muted; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 0.7 }
                Text { text: "Elige una superficie; todos los componentes comparten los mismos tokens."; color: Theme.faint; font.pixelSize: 10 }
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { text: wizz.language === "en" ? "Application language" : "Idioma de la aplicación"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                        Text { text: wizz.language === "en" ? "English is the beta default; Spanish remains available." : "English es el idioma predeterminado de la beta."; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: 10 }
                    }
                    WizComboBox {
                        id: languageBox; Layout.preferredWidth: 150; Layout.preferredHeight: 40
                        model: ["English", "Español"]
                        currentIndex: wizz.language === "es" ? 1 : 0
                        onActivated: wizz.setLanguage(currentIndex === 1 ? "es" : "en")
                        contentItem: Text { leftPadding: 13; text: languageBox.displayText; color: Theme.text; verticalAlignment: Text.AlignVCenter; font.pixelSize: 11 }
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
                            {name:"midnight",label:"Medianoche",color:"#6697ff"},{name:"ocean",label:"Océano",color:"#42c5dc"},
                            {name:"violet",label:"Violeta",color:"#a577ff"},{name:"forest",label:"Bosque",color:"#58d69a"},
                            {name:"ember",label:"Ámbar",color:"#ff8663"},{name:"rose",label:"Rosa",color:"#fa72bb"},
                            {name:"coral",label:"Coral",color:"#ff7b8b"},{name:"lime",label:"Lima",color:"#9de85b"},
                            {name:"cobalt",label:"Cobalto",color:"#5f8fff"},{name:"sunset",label:"Atardecer",color:"#ff9d5c"},
                            {name:"oled",label:"OLED",color:"#10121a"},{name:"light",label:"Claro",color:"#f6f8fc"}
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
                                Text { Layout.fillWidth: true; text: themeCard.modelData.label; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 11; font.weight: Font.Bold }
                                Text { visible: themeCard.selected; text: "✓"; color: Theme.primary; font.pixelSize: 14; font.weight: Font.Bold }
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
                            Text { text: "Reducir animaciones"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                            Text { text: "Elimina transiciones no esenciales y mantiene la respuesta inmediata."; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: 10 }
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
                            Text { text: "Icono con color de las luces"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 12; font.weight: Font.Bold }
                            Text { text: "Tiñe sólo el icono WiZ con el estado actual; desactívalo para usar el color del tema."; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: 10 }
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
            Layout.fillWidth: true; Layout.preferredHeight: 126; radius: Theme.radiusMedium
            color: Theme.card; border.width: 1; border.color: Theme.stroke
            RowLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 14
                Rectangle { Layout.preferredWidth: 46; Layout.preferredHeight: 46; radius: 14; color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.16); Text { anchors.centerIn: parent; text: "◈"; color: Theme.primary; font.pixelSize: 20 } }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 3
                    Text { text: wizz.appProduct + " · " + wizz.appVersion; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 13; font.weight: Font.Bold }
                    Text { Layout.fillWidth: true; text: wizz.updateStatus; color: Theme.muted; font.family: Theme.uiFont; font.pixelSize: 10; elide: Text.ElideRight }
                    RowLayout {
                        spacing: 6
                        Text { text: "Canal"; color: Theme.faint; font.family: Theme.uiFont; font.pixelSize: 10 }
                        PressSurface { Layout.preferredWidth: 64; Layout.preferredHeight: 25; radius: 12; color: wizz.updateChannel === "stable" ? Theme.primary : "transparent"; outlined: wizz.updateChannel !== "stable"; border.color: Theme.stroke; accentColor: Theme.primary; onClicked: wizz.setUpdateChannel("stable"); Text { anchors.centerIn: parent; text: "Estable"; color: wizz.updateChannel === "stable" ? "white" : Theme.muted; font.family: Theme.controlFont; font.pixelSize: 9; font.weight: Font.Bold } }
                        PressSurface { Layout.preferredWidth: 54; Layout.preferredHeight: 25; radius: 12; color: wizz.updateChannel === "beta" ? Theme.primary : "transparent"; outlined: wizz.updateChannel !== "beta"; border.color: Theme.stroke; accentColor: Theme.primary; onClicked: wizz.setUpdateChannel("beta"); Text { anchors.centerIn: parent; text: "Beta"; color: wizz.updateChannel === "beta" ? "white" : Theme.muted; font.family: Theme.controlFont; font.pixelSize: 9; font.weight: Font.Bold } }
                    }
                }
                ColumnLayout {
                    spacing: 7
                    PressSurface { Layout.preferredWidth: 142; Layout.preferredHeight: 32; radius: 16; color: "transparent"; outlined: true; border.color: Theme.stroke; accentColor: Theme.primary; enabled: !wizz.updateInProgress; onClicked: wizz.checkUpdates(); Text { anchors.centerIn: parent; text: wizz.updateInProgress ? "Buscando…" : "Buscar actualización"; color: Theme.text; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold } }
                    PressSurface { Layout.preferredWidth: 142; Layout.preferredHeight: 32; radius: 16; visible: wizz.updateAvailable; color: Theme.primary; accentColor: Theme.primary; enabled: !wizz.updateInProgress; onClicked: { if (wizz.updateCanInstall) wizz.installUpdate(); else Qt.openUrlExternally(wizz.updateUrl) } Text { anchors.centerIn: parent; text: wizz.updateCanInstall ? "Instalar y reiniciar" : "Abrir descarga"; color: "white"; font.family: Theme.controlFont; font.pixelSize: 10; font.weight: Font.Bold } }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Text { text: "AMPOLLETAS"; color: Theme.muted; font.pixelSize: 11; font.weight: Font.Bold; font.letterSpacing: 0.7 }
            Item { Layout.fillWidth: true }
            Text { text: wizz.scanMessage; color: Theme.faint; font.pixelSize: 10 }
        }
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 66; visible: wizz.totalCount === 0
            radius: 14; color: Theme.card; border.width: 1; border.color: Theme.stroke
            Text { anchors.centerIn: parent; text: "No hay ampolletas vinculadas. Usa Buscar luces o agrega una IP."; color: Theme.muted; font.pixelSize: 11 }
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
                        Rectangle { Layout.preferredWidth: 44; Layout.preferredHeight: 44; radius: 14; color: Qt.rgba(deviceCard.accentColor.r, deviceCard.accentColor.g, deviceCard.accentColor.b, 0.16); Text { anchors.centerIn: parent; text: "●"; color: deviceCard.accentColor; font.pixelSize: 17 } }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Text { Layout.fillWidth: true; text: deviceCard.displayName; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold; elide: Text.ElideRight }
                            Text { text: deviceCard.address; color: Theme.muted; font.pixelSize: 11 }
                            Text { Layout.fillWidth: true; text: (deviceCard.isOnline ? "En línea" : "Sin respuesta") + (deviceCard.moduleName ? " · " + deviceCard.moduleName : ""); color: Theme.faint; font.pixelSize: 9; elide: Text.ElideRight }
                        }
                        Rectangle { Layout.preferredWidth: 9; Layout.preferredHeight: 9; radius: 5; color: deviceCard.isSelected ? Theme.primary : Theme.stroke }
                        PressSurface {
                            Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17
                            color: deviceCard.address === wizz.activeLightIp ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.18) : "transparent"
                            accentColor: Theme.primary
                            onClicked: wizz.setActiveLight(deviceCard.address)
                            Text { anchors.centerIn: parent; text: "◎"; color: Theme.primary; font.pixelSize: 17 }
                        }
                        PressSurface {
                            Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17
                            color: "transparent"; accentColor: Theme.primary
                            onClicked: root.openInfo(deviceCard.address)
                            Text { anchors.centerIn: parent; text: "i"; color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 16; font.weight: Font.Bold }
                        }
                        PressSurface { Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17; color: "transparent"; border.width: 0; onClicked: root.openRename(deviceCard.address, deviceCard.displayName); Text { anchors.centerIn: parent; text: "✎"; color: Theme.primary; font.pixelSize: 15 } }
                        PressSurface { Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17; color: "transparent"; border.width: 0; accentColor: Theme.error; onClicked: { root.deletingIp = deviceCard.address; root.deletingName = deviceCard.displayName; deleteDialog.open() } Text { anchors.centerIn: parent; text: "×"; color: Theme.error; font.pixelSize: 20 } }
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
                ColumnLayout { Layout.fillWidth: true; spacing: 2; Text { text: root.selectedInfo.name || "Ampolleta WiZ"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 21; font.weight: Font.Bold } Text { text: "Información del dispositivo"; color: Theme.muted; font.pixelSize: 11 } }
                PressSurface { Layout.preferredWidth: 32; Layout.preferredHeight: 32; radius: 16; color: "transparent"; onClicked: infoDialog.close(); Text { anchors.centerIn: parent; text: "×"; color: Theme.muted; font.pixelSize: 22 } }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke }
            GridLayout {
                Layout.fillWidth: true; columns: 2; columnSpacing: 12; rowSpacing: 8
                Repeater {
                    model: [
                        {label:"IP", value:root.selectedInfo.ip || "—"}, {label:"MAC", value:root.selectedInfo.mac || "—"},
                        {label:"Estado", value:root.selectedInfo.online ? "En línea" : "Sin respuesta"}, {label:"Módulo", value:root.selectedInfo.module || "—"},
                        {label:"Brillo", value:(root.selectedInfo.brightness || 0) + "%"}, {label:"Temperatura", value:root.selectedInfo.kelvin ? root.selectedInfo.kelvin + "K" : "—"},
                        {label:"RGB", value:root.selectedInfo.rgb ? "Compatible" : "No disponible"}, {label:"Blancos", value:root.selectedInfo.tunableWhite ? "Compatible" : "No disponible"},
                        {label:"Rango CCT", value:root.selectedInfo.kelvinMin ? root.selectedInfo.kelvinMin + "–" + root.selectedInfo.kelvinMax + "K" : "—"}, {label:"Firmware", value:root.selectedInfo.firmware || "—"}
                    ]
                    delegate: Rectangle { required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 54; radius: 11; color: Theme.cardHi; border.width: 1; border.color: Theme.stroke; Column { anchors.fill: parent; anchors.margins: 10; spacing: 3; Text { text: modelData.label.toUpperCase(); color: Theme.faint; font.pixelSize: 9; font.weight: Font.Bold } Text { width: parent.width; text: modelData.value; color: Theme.text; font.pixelSize: 11; font.weight: Font.DemiBold; elide: Text.ElideRight } } }
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
                    Text { anchors.centerIn: parent; text: "Usar como activa"; color: "white"; font.family: Theme.controlFont; font.pixelSize: 11; font.weight: Font.Bold }
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
            Text { text: "Agregar por IP"; color: Theme.text; font.pixelSize: 21; font.weight: Font.Bold }
            Text { text: "La ampolleta debe estar conectada a la misma red local."; color: Theme.muted; font.pixelSize: 11 }
            TextField { id: ipField; Layout.fillWidth: true; Layout.preferredHeight: 44; placeholderText: "192.168.1.20"; color: Theme.text; placeholderTextColor: Theme.faint; leftPadding: 13; background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: ipField.activeFocus ? Theme.primary : Theme.stroke } }
            Item { Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } PressSurface { Layout.preferredWidth: 96; Layout.preferredHeight: 38; radius: 19; color: "transparent"; onClicked: addDialog.close(); Text { anchors.centerIn: parent; text: "Cancelar"; color: Theme.text; font.pixelSize: 11 } } PressSurface { Layout.preferredWidth: 106; Layout.preferredHeight: 38; radius: 19; color: Theme.primary; onClicked: { if (wizz.addLight(ipField.text)) { ipField.text = ""; addDialog.close() } } Text { anchors.centerIn: parent; text: "Agregar"; color: "white"; font.pixelSize: 11; font.weight: Font.Bold } } }
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
            Text { text: "Renombrar ampolleta"; color: Theme.text; font.pixelSize: 21; font.weight: Font.Bold }
            TextField { id: renameField; Layout.fillWidth: true; Layout.preferredHeight: 44; color: Theme.text; leftPadding: 13; background: Rectangle { color: Theme.bg; radius: 11; border.width: 1; border.color: renameField.activeFocus ? Theme.primary : Theme.stroke } }
            Item { Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } PressSurface { Layout.preferredWidth: 96; Layout.preferredHeight: 38; radius: 19; color: "transparent"; onClicked: renameDialog.close(); Text { anchors.centerIn: parent; text: "Cancelar"; color: Theme.text; font.pixelSize: 11 } } PressSurface { Layout.preferredWidth: 106; Layout.preferredHeight: 38; radius: 19; color: Theme.primary; onClicked: { if (wizz.renameLight(root.editingIp, renameField.text)) renameDialog.close() } Text { anchors.centerIn: parent; text: "Guardar"; color: "white"; font.pixelSize: 11; font.weight: Font.Bold } } }
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
            Text { text: "Quitar ampolleta"; color: Theme.text; font.pixelSize: 21; font.weight: Font.Bold }
            Text { Layout.fillWidth: true; text: "¿Quieres quitar “" + root.deletingName + "”? Puedes recuperarla con una búsqueda posterior."; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap }
            Item { Layout.fillHeight: true }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } PressSurface { Layout.preferredWidth: 96; Layout.preferredHeight: 38; radius: 19; color: "transparent"; onClicked: deleteDialog.close(); Text { anchors.centerIn: parent; text: "Cancelar"; color: Theme.text; font.pixelSize: 11 } } PressSurface { Layout.preferredWidth: 106; Layout.preferredHeight: 38; radius: 19; color: Theme.error; accentColor: Theme.error; onClicked: { wizz.removeLight(root.deletingIp); deleteDialog.close() } Text { anchors.centerIn: parent; text: "Quitar"; color: "white"; font.pixelSize: 11; font.weight: Font.Bold } } }
        }
    }
}
