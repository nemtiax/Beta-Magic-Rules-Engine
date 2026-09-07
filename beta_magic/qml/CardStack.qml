import QtQuick

Item {
    id: cardStack
    required property var cards
    property bool cardsInteractive: true
    property bool selectionOnly: false
    property bool targetable: false
    property int overlap: 46
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)

    readonly property int cardWidth: 108
    width: cardWidth
    height: cardColumn.implicitHeight

    Column {
        id: cardColumn
        spacing: -cardStack.overlap

        Repeater {
            model: cardStack.cards
            delegate: AttachmentStack {
                required property var modelData
                required property int index
                z: index
                cardData: modelData
                interactive: cardStack.cardsInteractive
                selectionOnly: cardStack.selectionOnly
                targetable: cardStack.targetable && cardData.legalTarget
                onSelected: function(cardId) { cardStack.selected(cardId) }
                onActivated: function(cardId) { cardStack.activated(cardId) }
                onAbilityActivated: function(cardId, abilityIndex) {
                    cardStack.abilityActivated(cardId, abilityIndex)
                }
                onInspected: function(cardData) { cardStack.inspected(cardData) }
            }
        }
    }
}
