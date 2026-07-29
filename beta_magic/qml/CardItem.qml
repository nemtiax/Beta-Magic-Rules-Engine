import QtQuick
import QtQuick.Controls

Rectangle {
    id: card
    required property var cardData
    property bool interactive: true
    property bool targetable: false
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)

    width: 126
    height: 82
    radius: 7
    color: cardData.background
    border.color: cardData.selected ? "#ffd54a" : "#262626"
    border.width: cardData.selected ? 4 : 2
    rotation: cardData.tapped ? 7 : 0
    scale: mouse.containsMouse && (interactive || targetable) ? 1.035 : 1.0

    Behavior on scale { NumberAnimation { duration: 90 } }
    Behavior on rotation { NumberAnimation { duration: 130 } }
    Behavior on border.width { NumberAnimation { duration: 80 } }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 7
        radius: 4
        color: "transparent"
        border.color: cardData.foreground
        border.width: 1
        opacity: 0.7
    }

    Text {
        anchors.top: parent.top
        anchors.topMargin: 14
        anchors.left: parent.left
        anchors.leftMargin: 9
        width: parent.width - 45
        text: cardData.name
        color: cardData.foreground
        font.bold: true
        font.pixelSize: 13
        horizontalAlignment: Text.AlignLeft
        wrapMode: Text.WordWrap
    }

    Text {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 9
        text: cardData.manaCost
        color: cardData.foreground
        font.bold: true
        font.pixelSize: 13
    }

    Text {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10
        anchors.horizontalCenter: parent.horizontalCenter
        visible: cardData.isCreature
        text: cardData.power + "/" + cardData.toughness
              + (cardData.damage ? "  · " + cardData.damage + " damage" : "")
        color: cardData.foreground
        font.pixelSize: 12
    }

    Text {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 7
        visible: cardData.tapped
        text: "T"
        color: cardData.foreground
        font.bold: true
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: card.interactive || card.targetable
                         ? Qt.LeftButton | Qt.RightButton : Qt.NoButton
        onEntered: card.inspected(cardData)
        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                if (cardData.activatedAbilities.length)
                    abilityMenu.popup()
            } else {
                card.selected(cardData.id)
            }
        }
        onDoubleClicked: function(mouse) {
            if (mouse.button !== Qt.LeftButton)
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
