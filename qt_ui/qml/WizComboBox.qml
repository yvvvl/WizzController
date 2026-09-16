import QtQuick
import QtQuick.Controls.Basic

// One themed menu surface for every selector in the desktop shell.  Qt Basic
// otherwise renders the popup with the platform's white fallback palette.
ComboBox {
    id: control
    font.family: Theme.controlFont
    font.pixelSize: 11
    // Opt-in search keeps compact selectors simple while large scene and
    // library catalogues become directly navigable.
    property bool searchable: false
    property string filterText: ""
    // Models that carry this role render a quiet category header before the
    // first matching item. This turns large libraries into a scan-friendly
    // catalogue without changing the compact selector itself.
    property string sectionRole: ""

    function sectionAt(index) {
        if (!sectionRole || !model || index < 0)
            return ""
        const entry = model[index]
        return entry && entry[sectionRole] ? String(entry[sectionRole]) : ""
    }

    delegate: ItemDelegate {
        required property int index
        readonly property bool matchesFilter: !control.searchable
                                             || control.textAt(index).toLowerCase().indexOf(control.filterText.toLowerCase()) >= 0
        readonly property string sectionName: control.sectionAt(index)
        readonly property bool beginsSection: sectionName.length > 0
                                                   && sectionName !== control.sectionAt(index - 1)
        width: ListView.view ? ListView.view.width : control.width
        height: matchesFilter ? 38 + (beginsSection ? 23 : 0) : 0
        visible: matchesFilter
        highlighted: control.highlightedIndex === index
        contentItem: Item {
            Text {
                visible: beginsSection
                width: parent.width
                height: visible ? 23 : 0
                leftPadding: 13; rightPadding: 13
                text: sectionName.toUpperCase()
                color: Theme.primary
                font.family: Theme.controlFont
                font.pixelSize: 9
                font.weight: Font.Bold
                font.letterSpacing: 0.7
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            Text {
                anchors.left: parent.left; anchors.right: parent.right
                anchors.top: parent.top; anchors.bottom: parent.bottom
                anchors.topMargin: beginsSection ? 23 : 0
                leftPadding: 13; rightPadding: 13
                text: control.textAt(index)
                color: Theme.text
                font: control.font
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }
        background: Rectangle {
            radius: 9
            color: highlighted
                ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.19)
                : parent.hovered ? Theme.cardHi : "transparent"
        }
    }

    popup: Popup {
        y: control.height + 6
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 12, 244)
        padding: 6
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle {
            color: Theme.card
            radius: 12
            border.width: 1
            border.color: Theme.stroke
        }
        contentItem: Column {
            spacing: 6
            TextField {
                id: filterField
                visible: control.searchable
                width: parent.width; height: 34
                placeholderText: "Buscar…"; placeholderTextColor: Theme.faint
                color: Theme.text; font: control.font; leftPadding: 10; rightPadding: 10
                onTextEdited: control.filterText = text
                background: Rectangle { color: Theme.bg; radius: 9; border.width: 1; border.color: filterField.activeFocus ? Theme.primary : Theme.stroke }
            }
            Text {
                visible: control.searchable
                width: parent.width; height: visible ? 16 : 0
                leftPadding: 4
                text: control.filterText.length ? "Coincidencias" : control.count + " opciones"
                color: Theme.faint
                font.family: Theme.controlFont
                font.pixelSize: 9
            }
            ListView {
                width: parent.width
                height: Math.min(contentHeight, control.searchable ? 178 : 232)
                clip: true
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
                spacing: 2
                ScrollIndicator.vertical: ScrollIndicator { }
            }
        }
    }
}
