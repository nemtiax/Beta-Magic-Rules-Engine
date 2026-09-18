import QtQuick
import QtQuick.Controls

Rectangle {
    id: card
    required property var cardData
    property bool interactive: true
    property bool selectionOnly: false
    property bool targetable: false
    property bool tabMode: false
    // Delegates can briefly outlive their model row while a model is being
    // replaced. Some optional panels also have no card until they become
    // active. Avoid feeding `undefined` into strongly typed QML properties
    // during those normal lifecycle transitions.
    readonly property var safeData: cardData || ({})
    function field(name, fallbackValue) {
        var value = safeData[name]
        return value === undefined || value === null ? fallbackValue : value
    }
    readonly property string artCropUrl: field("artCropUrl", "")
    readonly property color backgroundColor: field("background", "#b8b4ad")
    readonly property color foregroundColor: field("foreground", "#202020")
    readonly property var abilities: field("activatedAbilities", [])
    readonly property var counterData: field("counters", [])
    readonly property bool hasArt: artCropUrl.length > 0
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)

    width: 108
    height: tabMode ? 30 : 68
    radius: 7
    color: card.backgroundColor
    border.color: card.field("selected", false) ? "#ffd54a"
                  : card.field("balanceEligible", false)
                    || card.field("lichEligible", false)
                    || card.field("upkeepSacrificeEligible", false)
                    || card.field("riverChoiceEligible", false)
                    || card.field("maskChoiceEligible", false)
                    ? "#7fc8ff"
                  : card.field("combatRole", "") === "attacker" ? "#e58a55"
                  : card.field("combatRole", "") === "blocker" ? "#75b7e8"
                  : "#262626"
    border.width: card.field("selected", false) ? 4
                  : card.field("combatRole", "") ? 3 : 2
    rotation: card.field("tapped", false) ? 7 : 0
    scale: mouse.containsMouse && (interactive || targetable) ? 1.035 : 1.0

    Behavior on scale { NumberAnimation { duration: 90 } }
    Behavior on rotation { NumberAnimation { duration: 130 } }
    Behavior on border.width { NumberAnimation { duration: 80 } }

    Rectangle {
        anchors.fill: parent
        anchors.margins: card.tabMode ? 3 : 4
        radius: 4
        color: card.backgroundColor
        clip: true

        Image {
            anchors.fill: parent
            source: card.artCropUrl
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            cache: true
            smooth: true
            mipmap: true
            visible: card.hasArt && status !== Image.Error
        }
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: card.tabMode ? 3 : 5
        radius: 4
        color: "transparent"
        border.color: card.foregroundColor
        border.width: 1
        opacity: 0.7
    }

    Text {
        anchors.top: parent.top
        anchors.topMargin: card.tabMode ? 5 : 11
        anchors.left: parent.left
        anchors.leftMargin: card.tabMode ? 5 : 7
        width: parent.width - (card.tabMode ? 34 : 39)
        text: card.field("name", "")
        color: card.hasArt ? "white" : card.foregroundColor
        font.bold: true
        font.pixelSize: card.tabMode ? 10 : 12
        style: card.hasArt ? Text.Outline : Text.Normal
        styleColor: "#d9000000"
        horizontalAlignment: Text.AlignLeft
        wrapMode: card.tabMode ? Text.NoWrap : Text.WordWrap
        elide: card.tabMode ? Text.ElideRight : Text.ElideNone
    }

    Text {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: card.tabMode ? 5 : 7
        text: card.field("manaCost", "")
        color: card.hasArt ? "white" : card.foregroundColor
        font.bold: true
        font.pixelSize: card.tabMode ? 10 : 12
        style: card.hasArt ? Text.Outline : Text.Normal
        styleColor: "#d9000000"
    }

    Text {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: card.field("combatLabel", "") ? 20 : 7
        anchors.right: parent.right
        anchors.rightMargin: 8
        visible: !card.tabMode && card.field("isCreature", false)
        text: card.field("power", "") + "/" + card.field("toughness", "")
              + (card.field("damage", 0)
                 ? "  · " + card.field("damage", 0) + " damage" : "")
        color: card.hasArt ? "white" : card.foregroundColor
        font.pixelSize: 11
        font.bold: card.hasArt
        style: card.hasArt ? Text.Outline : Text.Normal
        styleColor: "#d9000000"
    }

    Text {
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.bottom: parent.bottom
        anchors.bottomMargin: card.field("combatLabel", "") ? 20 : 7
        width: parent.width - 48
        visible: !card.tabMode && card.counterData.length > 0
        text: {
            var labels = []
            for (var i = 0; i < card.counterData.length; ++i) {
                var counter = card.counterData[i]
                labels.push(counter.amount + " " + counter.name)
            }
            return labels.join(", ")
        }
        color: card.hasArt ? "white" : card.foregroundColor
        font.pixelSize: 9
        font.bold: true
        style: card.hasArt ? Text.Outline : Text.Normal
        styleColor: "#d9000000"
        elide: Text.ElideRight
    }

    Rectangle {
        id: combatBadge
        visible: !card.tabMode && !!card.field("combatLabel", "")
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 4
        height: 15
        radius: 4
        color: card.field("combatRole", "") === "attacker"
               ? "#7a3f26" : "#285875"
        border.color: card.field("combatRole", "") === "attacker"
                      ? "#f0a06d" : "#8ac9f3"

        Text {
            anchors.fill: parent
            anchors.leftMargin: 4
            anchors.rightMargin: 4
            text: card.field("combatLabel", "")
            color: "#ffffff"
            font.bold: true
            font.pixelSize: 9
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

    }

    Rectangle {
        id: riverBadge
        visible: !card.tabMode && !!card.field("riverSide", "")
        x: card.field("riverSide", "") === "L" ? 4 : parent.width - width - 4
        anchors.verticalCenter: parent.verticalCenter
        width: 18
        height: 22
        radius: 5
        color: card.field("riverSide", "") === "L" ? "#276d94" : "#9a4e31"
        border.color: "#eaf5ff"
        border.width: 1
        z: 4

        Text {
            anchors.centerIn: parent
            text: card.field("riverSide", "")
            color: "#ffffff"
            font.bold: true
            font.pixelSize: 11
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: card.selectionOnly
                         ? ((card.field("attackerSelectionActive", false)
                             && !card.field("attackerEligible", false))
                            || (card.field("riverChoiceActive", false)
                                && !card.field("riverChoiceEligible", false))
                            || (card.field("maskChoiceActive", false)
                                && !card.field("maskChoiceEligible", false))
                            ? Qt.NoButton : Qt.LeftButton)
                         : card.interactive || card.targetable
                           ? Qt.LeftButton | Qt.RightButton : Qt.NoButton
        onEntered: card.inspected(cardData)
        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                if (!card.selectionOnly && card.abilities.length)
                    abilityMenu.popup()
            } else {
                card.selected(card.field("id", ""))
            }
        }
        onDoubleClicked: function(mouse) {
            if (mouse.button !== Qt.LeftButton)
                return
            if (card.selectionOnly)
                return
            if (card.abilities.length === 1) {
                if (card.abilities[0].enabled)
                    card.abilityActivated(
                        card.field("id", ""), card.abilities[0].index)
            }
            else if (card.abilities.length > 1)
                abilityMenu.popup()
            else if (card.field("actionEnabled", false))
                card.activated(card.field("id", ""))
        }
    }

    Menu {
        id: abilityMenu
        y: card.height
        Repeater {
            model: card.abilities
            delegate: MenuItem {
                required property var modelData
                text: modelData.label
                enabled: modelData.enabled
                onTriggered: card.abilityActivated(
                                 card.field("id", ""), modelData.index)
            }
        }
    }
}
