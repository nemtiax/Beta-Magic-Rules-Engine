import QtQuick
import QtQuick.Controls

Frame {
    id: handPanel
    required property var playerData
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)

    padding: 8
    background: Rectangle {
        color: "#252c35"
        border.color: "#729fcf"
        radius: 8
    }

    CardFlow {
        anchors.fill: parent
        cards: playerData.hand
        interactive: true
        onSelected: function(cardId) { handPanel.selected(cardId) }
        onActivated: function(cardId) { handPanel.activated(cardId) }
        onAbilityActivated: function(cardId, abilityIndex) {
            handPanel.abilityActivated(cardId, abilityIndex)
        }
        onInspected: function(cardData) { handPanel.inspected(cardData) }
    }
}
