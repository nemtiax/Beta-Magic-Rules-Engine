import QtQuick
import QtQuick.Controls

Rectangle {
    id: card
    required property var cardData
    property bool interactive: true
    property bool selectionOnly: false
    property bool targetable: false
    property bool tabMode: false
    readonly property bool hasArt: cardData.artCropUrl
                                    && cardData.artCropUrl.toString().length > 0
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)

    width: 108
    height: tabMode ? 30 : 68
    radius: 7
    color: cardData.background
    border.color: cardData.selected ? "#ffd54a"
                  : cardData.balanceEligible || cardData.lichEligible
                    || cardData.upkeepSacrificeEligible
                    ? "#7fc8ff"
                  : cardData.combatRole === "attacker" ? "#e58a55"
                  : cardData.combatRole === "blocker" ? "#75b7e8"
                  : "#262626"
    border.width: cardData.selected ? 4 : cardData.combatRole ? 3 : 2
    rotation: cardData.tapped ? 7 : 0
    scale: mouse.containsMouse && (interactive || targetable) ? 1.035 : 1.0

    Behavior on scale { NumberAnimation { duration: 90 } }
    Behavior on rotation { NumberAnimation { duration: 130 } }
    Behavior on border.width { NumberAnimation { duration: 80 } }

    Rectangle {
        anchors.fill: parent
        anchors.margins: card.tabMode ? 3 : 4
        radius: 4
        color: cardData.background
        clip: true

        Image {
            anchors.fill: parent
            source: cardData.artCropUrl || ""
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
        border.color: cardData.foreground
        border.width: 1
        opacity: 0.7
    }

    Text {
        anchors.top: parent.top
        anchors.topMargin: card.tabMode ? 5 : 11
        anchors.left: parent.left
        anchors.leftMargin: card.tabMode ? 5 : 7
        width: parent.width - (card.tabMode ? 34 : 39)
        text: cardData.name
        color: card.hasArt ? "white" : cardData.foreground
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
        text: cardData.manaCost
        color: card.hasArt ? "white" : cardData.foreground
        font.bold: true
        font.pixelSize: card.tabMode ? 10 : 12
        style: card.hasArt ? Text.Outline : Text.Normal
        styleColor: "#d9000000"
    }

    Text {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: cardData.combatLabel ? 20 : 7
        anchors.right: parent.right
        anchors.rightMargin: 8
        visible: !card.tabMode && cardData.isCreature
        text: cardData.power + "/" + cardData.toughness
              + (cardData.damage ? "  · " + cardData.damage + " damage" : "")
        color: card.hasArt ? "white" : cardData.foreground
        font.pixelSize: 11
        font.bold: card.hasArt
        style: card.hasArt ? Text.Outline : Text.Normal
        styleColor: "#d9000000"
    }

    Rectangle {
        id: combatBadge
        visible: !card.tabMode && !!cardData.combatLabel
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 4
        height: 15
        radius: 4
        color: cardData.combatRole === "attacker" ? "#7a3f26" : "#285875"
        border.color: cardData.combatRole === "attacker" ? "#f0a06d" : "#8ac9f3"

        Text {
            anchors.fill: parent
            anchors.leftMargin: 4
            anchors.rightMargin: 4
            text: cardData.combatLabel
            color: "#ffffff"
            font.bold: true
            font.pixelSize: 9
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: card.selectionOnly
                         ? (cardData.attackerSelectionActive
                            && !cardData.attackerEligible
                            ? Qt.NoButton : Qt.LeftButton)
                         : card.interactive || card.targetable
                           ? Qt.LeftButton | Qt.RightButton : Qt.NoButton
        onEntered: card.inspected(cardData)
        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                if (!card.selectionOnly && cardData.activatedAbilities.length)
                    abilityMenu.popup()
            } else {
                card.selected(cardData.id)
            }
        }
        onDoubleClicked: function(mouse) {
            if (mouse.button !== Qt.LeftButton)
                return
            if (card.selectionOnly)
                return
            if (cardData.activatedAbilities.length === 1)
                card.abilityActivated(
                    cardData.id, cardData.activatedAbilities[0].index)
            else if (cardData.activatedAbilities.length > 1)
                abilityMenu.popup()
            else
                card.activated(cardData.id)
        }
    }

    Menu {
        id: abilityMenu
        y: card.height
        Repeater {
            model: cardData.activatedAbilities
            delegate: MenuItem {
                required property var modelData
                text: modelData.label
                enabled: modelData.enabled
                onTriggered: card.abilityActivated(cardData.id, modelData.index)
            }
        }
    }
}
