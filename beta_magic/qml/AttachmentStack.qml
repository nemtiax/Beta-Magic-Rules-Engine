import QtQuick

Item {
    id: stack
    required property var cardData
    property bool interactive: true
    property bool targetable: false
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)

    readonly property int tabOffset: 18
    readonly property int attachmentCount: cardData.attachments
                                           ? cardData.attachments.length : 0
    width: 108
    height: 68 + attachmentCount * tabOffset

    Repeater {
        model: cardData.attachments || []
        delegate: CardItem {
            required property var modelData
            required property int index
            x: 0
            y: index * stack.tabOffset
            z: index
            tabMode: true
            cardData: modelData
            interactive: stack.interactive
            targetable: stack.targetable && cardData.legalTarget
            onSelected: function(cardId) { stack.selected(cardId) }
            onActivated: function(cardId) { stack.activated(cardId) }
            onAbilityActivated: function(cardId, abilityIndex) {
                stack.abilityActivated(cardId, abilityIndex)
            }
            onInspected: function(cardData) { stack.inspected(cardData) }
        }
    }

    CardItem {
        x: 0
        y: stack.attachmentCount * stack.tabOffset
        z: stack.attachmentCount + 1
        cardData: stack.cardData
        interactive: stack.interactive
        targetable: stack.targetable && cardData.legalTarget
        onSelected: function(cardId) { stack.selected(cardId) }
        onActivated: function(cardId) { stack.activated(cardId) }
        onAbilityActivated: function(cardId, abilityIndex) {
            stack.abilityActivated(cardId, abilityIndex)
        }
        onInspected: function(cardData) { stack.inspected(cardData) }
    }
}
