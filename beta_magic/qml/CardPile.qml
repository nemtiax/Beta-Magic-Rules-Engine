import QtQuick
import QtQuick.Controls

Flickable {
    id: pile
    required property var cards
    property bool cardsInteractive: false
    property bool selectionOnly: false
    property bool targetable: false
    property int edgeInset: 2
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)

    implicitWidth: 108 + edgeInset * 2
    implicitHeight: 72
    contentWidth: width
    contentHeight: Math.max(height, stack.height + edgeInset * 2)
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    flickableDirection: Flickable.VerticalFlick
    ScrollBar.vertical: ScrollBar {
        policy: stack.height + pile.edgeInset * 2 > pile.height
                ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
    }

    CardStack {
        id: stack
        x: pile.edgeInset
        y: pile.edgeInset
        cards: pile.cards
        cardsInteractive: pile.cardsInteractive
        selectionOnly: pile.selectionOnly
        targetable: pile.targetable
        onSelected: function(cardId) { pile.selected(cardId) }
        onActivated: function(cardId) { pile.activated(cardId) }
        onAbilityActivated: function(cardId, abilityIndex) {
            pile.abilityActivated(cardId, abilityIndex)
        }
        onInspected: function(cardData) { pile.inspected(cardData) }
    }
}
