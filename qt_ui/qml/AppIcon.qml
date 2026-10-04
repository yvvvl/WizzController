import QtQuick

Item {
    id: root
    implicitWidth: 24
    implicitHeight: 24
    property string glyph: ""
    property string name: ""
    property int sceneId: 0
    property color color: "white"
    property real strokeWidth: 1.8
    property bool filled: false

    readonly property string iconName: {
        if (name.length > 0) return name
        if (sceneId > 0) {
            switch (sceneId) {
            case 1: case 23: return "waves"
            case 16: return "waves"
            case 2: return "heart"
            case 3: case 9: return "sunrise"
            case 4: case 26: case 33: return "sparkles"
            case 5: case 29: return "flame"
            case 6: return "home"
            case 7: return "tree"
            case 8: case 17: return "palette"
            case 10: case 14: return "moon"
            case 11: return "brightness"
            case 12: return "sun"
            case 13: return "snowflake"
            case 15: return "focus"
            case 18: return "cinema"
            case 19: return "leaf"
            case 20: return "flower"
            case 21: return "sun"
            case 22: return "leaf"
            case 24: return "palm"
            case 25: return "glass"
            case 27: return "christmas"
            case 28: return "pumpkin"
            case 30: return "gem"
            case 31: return "pulse"
            case 32: return "settings"
            default: return "sparkles"
            }
        }
        switch (glyph) {
        case "\uE80F": return "home"
        case "\uE790": return "palette"
        case "\uE734": return "scenes"
        case "\uE945": return "routines"
        case "\uE713": return "settings"
        case "\uE765": return "keyboard"
        case "\uE7F4": return "cinema"
        case "\uE82D": return "book"
        case "\uE8CB": return "waves"
        case "\uE7FC": return "sparkles"
        case "\uE706": return "sun"
        case "\uE9CA": return "thermometer"
        case "\uE777": return "reset"
        case "\uE7E8": return "power"
        case "\uE70F": return "focus"
        case "\uE708": return "moon"
        case "\uE9C5": return "dim"
        case "\uEA80": return "bulb"
        case "\uE8B2": return "heart"
        case "\uE73E": return "check"
        case "\uE739": return "circle"
        case "\uE74D": return "trash"
        case "\uE8C8": return "duplicate"
        case "\uE7F8": return "star"
        case "\uE711": return "close"
        case "\uE921": return "minimize"
        case "\uE72A": return "arrowRight"
        case "×": return "close"
        case "↯": return "routines"
        case "✎": return "edit"
        case "ⓘ": return "info"
        case "◉": return "target"
        case "✓": return "check"
        case "⌨": return "keyboard"
        case "↑": return "arrowUp"
        case "↓": return "arrowDown"
        case "⌄": return "chevronDown"
        case "★": case "☆": return "star"
        case "✦": return "sparkles"
        case "+": return "plus"
        default: return "bulb"
        }
    }

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            const ctx = getContext("2d")
            const scaleX = width / 24
            const scaleY = height / 24
            ctx.reset()
            ctx.scale(scaleX, scaleY)
            ctx.strokeStyle = root.color
            ctx.fillStyle = root.color
            ctx.lineWidth = root.iconName === "close" ? 2.6 : root.strokeWidth
            ctx.lineCap = "round"
            ctx.lineJoin = "round"

            function strokePath(draw) {
                ctx.beginPath()
                draw()
                ctx.stroke()
            }
            function circle(x, y, r) {
                ctx.beginPath()
                ctx.arc(x, y, r, 0, Math.PI * 2)
                ctx.stroke()
            }

            switch (root.iconName) {
            case "home":
                strokePath(function() { ctx.moveTo(3, 10.5); ctx.lineTo(12, 3.5); ctx.lineTo(21, 10.5); ctx.moveTo(5.5, 9.5); ctx.lineTo(5.5, 20); ctx.lineTo(18.5, 20); ctx.lineTo(18.5, 9.5); ctx.moveTo(9.5, 20); ctx.lineTo(9.5, 14); ctx.lineTo(14.5, 14); ctx.lineTo(14.5, 20) })
                break
            case "palette":
                strokePath(function() { ctx.moveTo(12, 3); ctx.bezierCurveTo(6.8, 3, 3, 6.7, 3, 11.5); ctx.bezierCurveTo(3, 16.4, 6.7, 20, 11.2, 20); ctx.bezierCurveTo(13, 20, 13.8, 18.8, 13.8, 17.6); ctx.bezierCurveTo(13.8, 16.7, 13.2, 16.2, 13.2, 15.4); ctx.bezierCurveTo(13.2, 14.4, 14, 13.8, 15, 13.8); ctx.lineTo(17, 13.8); ctx.bezierCurveTo(19.5, 13.8, 21, 12.3, 21, 10.1); ctx.bezierCurveTo(21, 6.1, 17.1, 3, 12, 3) })
                circle(7.5, 10, 0.75); circle(11, 7.5, 0.75); circle(15, 7.5, 0.75)
                break
            case "scenes": case "star":
                strokePath(function() { ctx.moveTo(12, 3); ctx.lineTo(14.8, 8.8); ctx.lineTo(21, 9.7); ctx.lineTo(16.5, 14.1); ctx.lineTo(17.6, 20.3); ctx.lineTo(12, 17.3); ctx.lineTo(6.4, 20.3); ctx.lineTo(7.5, 14.1); ctx.lineTo(3, 9.7); ctx.lineTo(9.2, 8.8); ctx.closePath() })
                break
            case "routines":
                strokePath(function() { ctx.moveTo(10, 6); ctx.lineTo(20, 6); ctx.moveTo(10, 12); ctx.lineTo(20, 12); ctx.moveTo(10, 18); ctx.lineTo(20, 18) })
                circle(5, 6, 1.2); circle(5, 12, 1.2); circle(5, 18, 1.2)
                break
            case "settings":
                circle(12, 12, 3)
                strokePath(function() { ctx.moveTo(10, 3); ctx.lineTo(14, 3); ctx.lineTo(14.5, 5.2); ctx.lineTo(16.4, 6.3); ctx.lineTo(18.5, 5.5); ctx.lineTo(20.5, 9); ctx.lineTo(18.8, 10.5); ctx.lineTo(18.8, 13); ctx.lineTo(20.5, 15); ctx.lineTo(18.5, 18.5); ctx.lineTo(16.3, 17.7); ctx.lineTo(14.3, 18.8); ctx.lineTo(14, 21); ctx.lineTo(10, 21); ctx.lineTo(9.6, 18.8); ctx.lineTo(7.7, 17.7); ctx.lineTo(5.5, 18.5); ctx.lineTo(3.5, 15); ctx.lineTo(5.2, 13.5); ctx.lineTo(5.2, 11); ctx.lineTo(3.5, 9); ctx.lineTo(5.5, 5.5); ctx.lineTo(7.7, 6.3); ctx.lineTo(9.7, 5.2); ctx.closePath() })
                break
            case "keyboard":
                strokePath(function() { ctx.rect(2.5, 5, 19, 14); ctx.moveTo(6, 9); ctx.lineTo(7, 9); ctx.moveTo(10, 9); ctx.lineTo(11, 9); ctx.moveTo(14, 9); ctx.lineTo(15, 9); ctx.moveTo(18, 9); ctx.lineTo(19, 9); ctx.moveTo(6, 12); ctx.lineTo(7, 12); ctx.moveTo(10, 12); ctx.lineTo(11, 12); ctx.moveTo(14, 12); ctx.lineTo(15, 12); ctx.moveTo(18, 12); ctx.lineTo(19, 12); ctx.moveTo(8, 15.5); ctx.lineTo(16, 15.5) })
                break
            case "book":
                strokePath(function() { ctx.rect(5, 3, 14, 18); ctx.moveTo(8, 7); ctx.lineTo(16, 7); ctx.moveTo(8, 10); ctx.lineTo(16, 10); ctx.moveTo(8, 16); ctx.lineTo(16, 16) })
                break
            case "power":
                strokePath(function() { ctx.moveTo(12, 3); ctx.lineTo(12, 12); ctx.moveTo(6.4, 6.4); ctx.bezierCurveTo(3.1, 9.5, 3.2, 15, 6.5, 18.2); ctx.bezierCurveTo(9.7, 21.5, 15, 21.5, 18.3, 18.2); ctx.bezierCurveTo(21.6, 15, 21.6, 9.6, 18.4, 6.4) })
                break
            case "close":
                strokePath(function() { ctx.moveTo(6, 6); ctx.lineTo(18, 18); ctx.moveTo(18, 6); ctx.lineTo(6, 18) })
                break
            case "plus":
                strokePath(function() { ctx.moveTo(12, 4); ctx.lineTo(12, 20); ctx.moveTo(4, 12); ctx.lineTo(20, 12) })
                break
            case "minimize":
                strokePath(function() { ctx.moveTo(5, 12); ctx.lineTo(19, 12) })
                break
            case "arrowRight":
                strokePath(function() { ctx.moveTo(4, 12); ctx.lineTo(20, 12); ctx.moveTo(13, 5); ctx.lineTo(20, 12); ctx.lineTo(13, 19) })
                break
            case "circle":
                circle(12, 12, 7)
                break
            case "duplicate":
                strokePath(function() { ctx.moveTo(8, 8); ctx.lineTo(19, 8); ctx.lineTo(19, 20); ctx.lineTo(8, 20); ctx.closePath(); ctx.moveTo(15, 8); ctx.lineTo(15, 4); ctx.lineTo(4, 4); ctx.lineTo(4, 16); ctx.lineTo(8, 16) })
                break
            case "trash":
                strokePath(function() { ctx.moveTo(4, 7); ctx.lineTo(20, 7); ctx.moveTo(9, 4); ctx.lineTo(15, 4); ctx.moveTo(6, 7); ctx.lineTo(7, 20); ctx.lineTo(17, 20); ctx.lineTo(18, 7); ctx.moveTo(10, 10); ctx.lineTo(10, 17); ctx.moveTo(14, 10); ctx.lineTo(14, 17) })
                break
            case "chevronDown":
                strokePath(function() { ctx.moveTo(5, 9); ctx.lineTo(12, 16); ctx.lineTo(19, 9) })
                break
            case "arrowUp":
                strokePath(function() { ctx.moveTo(12, 20); ctx.lineTo(12, 4); ctx.moveTo(5, 11); ctx.lineTo(12, 4); ctx.lineTo(19, 11) })
                break
            case "arrowDown":
                strokePath(function() { ctx.moveTo(12, 4); ctx.lineTo(12, 20); ctx.moveTo(5, 13); ctx.lineTo(12, 20); ctx.lineTo(19, 13) })
                break
            case "edit":
                strokePath(function() { ctx.moveTo(14, 5); ctx.lineTo(19, 10); ctx.moveTo(4, 20); ctx.lineTo(8, 19); ctx.lineTo(19.5, 7.5); ctx.arc(18, 6, 2.1, -0.75, 2.35); ctx.lineTo(6.5, 17.5); ctx.lineTo(4, 20); ctx.moveTo(4, 20); ctx.lineTo(5, 16) })
                break
            case "info":
                circle(12, 12, 9)
                strokePath(function() { ctx.moveTo(12, 11); ctx.lineTo(12, 16); ctx.moveTo(12, 7.5); ctx.lineTo(12, 7.6) })
                break
            case "check":
                strokePath(function() { ctx.moveTo(4, 12.5); ctx.lineTo(9.5, 18); ctx.lineTo(20, 6) })
                break
            case "heart":
                ctx.beginPath()
                ctx.moveTo(12, 20)
                ctx.bezierCurveTo(10, 18.2, 4, 13.2, 4, 8.7)
                ctx.bezierCurveTo(4, 4.5, 9, 3.2, 12, 7)
                ctx.bezierCurveTo(15, 3.2, 20, 4.5, 20, 8.7)
                ctx.bezierCurveTo(20, 13.2, 14, 18.2, 12, 20)
                if (root.filled) ctx.fill(); else ctx.stroke()
                break
            case "sun": case "brightness":
                circle(12, 12, 4)
                strokePath(function() { ctx.moveTo(12, 2); ctx.lineTo(12, 5); ctx.moveTo(12, 19); ctx.lineTo(12, 22); ctx.moveTo(2, 12); ctx.lineTo(5, 12); ctx.moveTo(19, 12); ctx.lineTo(22, 12); ctx.moveTo(4.9, 4.9); ctx.lineTo(7, 7); ctx.moveTo(17, 17); ctx.lineTo(19.1, 19.1); ctx.moveTo(19.1, 4.9); ctx.lineTo(17, 7); ctx.moveTo(7, 17); ctx.lineTo(4.9, 19.1) })
                break
            case "thermometer":
                strokePath(function() { ctx.moveTo(14, 14.2); ctx.lineTo(14, 5.5); ctx.arc(12, 5.5, 2, 0, Math.PI * 2); ctx.lineTo(10, 14.2); ctx.bezierCurveTo(8.5, 15.1, 8, 16, 8, 17.5); ctx.arc(12, 17.5, 4, 0, Math.PI * 2) })
                break
            case "sparkles": case "party":
                strokePath(function() { ctx.moveTo(12, 2.5); ctx.lineTo(14, 9); ctx.lineTo(20.5, 11); ctx.lineTo(14, 13); ctx.lineTo(12, 19.5); ctx.lineTo(10, 13); ctx.lineTo(3.5, 11); ctx.lineTo(10, 9); ctx.closePath(); ctx.moveTo(19, 16); ctx.lineTo(20, 18.5); ctx.lineTo(22.5, 19.5); ctx.lineTo(20, 20.5); ctx.lineTo(19, 23); ctx.lineTo(18, 20.5); ctx.lineTo(15.5, 19.5); ctx.lineTo(18, 18.5); ctx.closePath() })
                break
            case "waves":
                strokePath(function() { ctx.moveTo(3, 8); ctx.bezierCurveTo(6, 5, 9, 5, 12, 8); ctx.bezierCurveTo(15, 11, 18, 11, 21, 8); ctx.moveTo(3, 13); ctx.bezierCurveTo(6, 10, 9, 10, 12, 13); ctx.bezierCurveTo(15, 16, 18, 16, 21, 13); ctx.moveTo(3, 18); ctx.bezierCurveTo(6, 15, 9, 15, 12, 18); ctx.bezierCurveTo(15, 21, 18, 21, 21, 18) })
                break
            case "sunrise":
                strokePath(function() { ctx.arc(12, 19, 6, Math.PI, Math.PI * 2); ctx.moveTo(3, 19); ctx.lineTo(21, 19); ctx.moveTo(12, 2); ctx.lineTo(12, 5); ctx.moveTo(4, 7); ctx.lineTo(6, 9); ctx.moveTo(20, 7); ctx.lineTo(18, 9) })
                break
            case "flame":
                strokePath(function() { ctx.moveTo(12, 22); ctx.bezierCurveTo(5, 21, 5, 15, 8, 11); ctx.bezierCurveTo(8, 15, 11, 16, 12, 13); ctx.bezierCurveTo(14, 9, 11, 6, 15, 3); ctx.bezierCurveTo(15, 9, 21, 11, 19, 17); ctx.bezierCurveTo(18, 20, 15, 22, 12, 22); ctx.closePath(); ctx.moveTo(12, 21); ctx.bezierCurveTo(9, 19, 10, 16, 13, 14); ctx.bezierCurveTo(13, 17, 16, 18, 15, 20) })
                break
            case "tree":
                strokePath(function() { ctx.moveTo(12, 21); ctx.lineTo(12, 5); ctx.moveTo(12, 12); ctx.lineTo(6, 8); ctx.moveTo(12, 15); ctx.lineTo(18, 10); ctx.moveTo(12, 18); ctx.lineTo(7, 14); ctx.moveTo(12, 8); ctx.lineTo(16, 5); ctx.moveTo(8, 21); ctx.lineTo(16, 21) })
                break
            case "leaf":
                strokePath(function() { ctx.moveTo(5, 19); ctx.bezierCurveTo(4, 8, 10, 3, 21, 3); ctx.bezierCurveTo(21, 14, 16, 20, 5, 19); ctx.moveTo(5, 19); ctx.bezierCurveTo(9, 14, 13, 11, 18, 7) })
                break
            case "palm":
                strokePath(function() { ctx.moveTo(12, 21); ctx.lineTo(13, 8); ctx.moveTo(13, 8); ctx.bezierCurveTo(8, 4, 5, 5, 3, 4); ctx.bezierCurveTo(6, 8, 9, 8, 13, 8); ctx.moveTo(13, 8); ctx.bezierCurveTo(15, 4, 18, 3, 21, 3); ctx.bezierCurveTo(19, 7, 16, 8, 13, 8); ctx.moveTo(13, 8); ctx.bezierCurveTo(13, 4, 12, 2, 10, 2); ctx.bezierCurveTo(10, 5, 11, 7, 13, 8); ctx.moveTo(9, 21); ctx.lineTo(16, 21) })
                break
            case "flower":
                circle(12, 12, 2)
                circle(12, 6, 3); circle(18, 12, 3); circle(12, 18, 3); circle(6, 12, 3)
                break
            case "snowflake":
                strokePath(function() { ctx.moveTo(12, 3); ctx.lineTo(12, 21); ctx.moveTo(4.2, 7.5); ctx.lineTo(19.8, 16.5); ctx.moveTo(19.8, 7.5); ctx.lineTo(4.2, 16.5); ctx.moveTo(12, 3); ctx.lineTo(9.5, 5.5); ctx.moveTo(12, 3); ctx.lineTo(14.5, 5.5); ctx.moveTo(12, 21); ctx.lineTo(9.5, 18.5); ctx.moveTo(12, 21); ctx.lineTo(14.5, 18.5) })
                break
            case "glass":
                strokePath(function() { ctx.moveTo(5, 3); ctx.lineTo(19, 3); ctx.lineTo(17, 11); ctx.bezierCurveTo(16, 14, 14, 15, 12, 15); ctx.bezierCurveTo(10, 15, 8, 14, 7, 11); ctx.closePath(); ctx.moveTo(12, 15); ctx.lineTo(12, 21); ctx.moveTo(8, 21); ctx.lineTo(16, 21); ctx.moveTo(7, 9); ctx.lineTo(17, 9) })
                break
            case "christmas":
                strokePath(function() { ctx.moveTo(12, 3); ctx.lineTo(7, 9); ctx.lineTo(10, 9); ctx.lineTo(5, 15); ctx.lineTo(10, 15); ctx.lineTo(7, 20); ctx.lineTo(17, 20); ctx.lineTo(14, 15); ctx.lineTo(19, 15); ctx.lineTo(14, 9); ctx.lineTo(17, 9); ctx.closePath(); ctx.moveTo(12, 20); ctx.lineTo(12, 22) })
                break
            case "pumpkin":
                strokePath(function() { ctx.moveTo(12, 6); ctx.lineTo(12, 3); ctx.lineTo(15, 3); ctx.moveTo(12, 6); ctx.bezierCurveTo(4, 4, 3, 9, 3, 14); ctx.bezierCurveTo(3, 20, 8, 21, 12, 19); ctx.bezierCurveTo(16, 21, 21, 20, 21, 14); ctx.bezierCurveTo(21, 9, 20, 4, 12, 6); ctx.moveTo(8, 10); ctx.lineTo(9, 12); ctx.moveTo(16, 10); ctx.lineTo(15, 12); ctx.moveTo(9, 16); ctx.lineTo(12, 17); ctx.lineTo(15, 16) })
                break
            case "gem":
                strokePath(function() { ctx.moveTo(7, 3); ctx.lineTo(17, 3); ctx.lineTo(22, 9); ctx.lineTo(12, 21); ctx.lineTo(2, 9); ctx.closePath(); ctx.moveTo(2, 9); ctx.lineTo(22, 9); ctx.moveTo(7, 3); ctx.lineTo(9, 9); ctx.lineTo(12, 21); ctx.lineTo(15, 9); ctx.lineTo(17, 3) })
                break
            case "pulse":
                strokePath(function() { ctx.moveTo(2, 13); ctx.lineTo(7, 13); ctx.lineTo(9, 7); ctx.lineTo(13, 18); ctx.lineTo(16, 11); ctx.lineTo(18, 13); ctx.lineTo(22, 13) })
                break
            case "moon":
                strokePath(function() { ctx.moveTo(19.5, 14.5); ctx.bezierCurveTo(15, 18.5, 8, 17, 6.5, 11); ctx.bezierCurveTo(5.8, 8.2, 6.8, 5.2, 9, 3.5); ctx.bezierCurveTo(4.8, 4.5, 2.5, 8.5, 3.5, 13); ctx.bezierCurveTo(4.8, 19, 11, 22, 16.5, 19); ctx.bezierCurveTo(18, 18.2, 19, 16.5, 19.5, 14.5) })
                break
            case "focus": case "target":
                circle(12, 12, 7.5); circle(12, 12, 3.5)
                strokePath(function() { ctx.moveTo(12, 2); ctx.lineTo(12, 5); ctx.moveTo(22, 12); ctx.lineTo(19, 12); ctx.moveTo(12, 22); ctx.lineTo(12, 19); ctx.moveTo(2, 12); ctx.lineTo(5, 12) })
                break
            case "reset":
                strokePath(function() { ctx.moveTo(20, 8); ctx.lineTo(20, 3); ctx.lineTo(15, 3); ctx.moveTo(19.5, 7.5); ctx.bezierCurveTo(17.6, 5.2, 15, 4, 12, 4); ctx.bezierCurveTo(7.6, 4, 4, 7.6, 4, 12); ctx.bezierCurveTo(4, 16.4, 7.6, 20, 12, 20); ctx.bezierCurveTo(15, 20, 17.5, 18.4, 19, 16) })
                break
            case "cinema": case "monitor":
                strokePath(function() { ctx.roundedRect(3, 4, 18, 13, 2, 2); ctx.moveTo(8, 21); ctx.lineTo(16, 21); ctx.moveTo(12, 17); ctx.lineTo(12, 21) })
                break
            case "dim":
                strokePath(function() { ctx.moveTo(5, 6); ctx.lineTo(19, 6); ctx.moveTo(7, 12); ctx.lineTo(17, 12); ctx.moveTo(9, 18); ctx.lineTo(15, 18) })
                break
            default:
                strokePath(function() { ctx.moveTo(8.5, 14.5); ctx.bezierCurveTo(8.5, 12.2, 5.5, 10.6, 5.5, 7.7); ctx.bezierCurveTo(5.5, 4, 8.3, 2, 12, 2); ctx.bezierCurveTo(15.7, 2, 18.5, 4, 18.5, 7.7); ctx.bezierCurveTo(18.5, 10.6, 15.5, 12.2, 15.5, 14.5); ctx.lineTo(8.5, 14.5); ctx.moveTo(9, 17); ctx.lineTo(15, 17); ctx.moveTo(10, 20); ctx.lineTo(14, 20) })
            }
        }
    }

    onIconNameChanged: canvas.requestPaint()
    onColorChanged: canvas.requestPaint()
    onStrokeWidthChanged: canvas.requestPaint()
    onFilledChanged: canvas.requestPaint()
    onWidthChanged: canvas.requestPaint()
    onHeightChanged: canvas.requestPaint()
}
