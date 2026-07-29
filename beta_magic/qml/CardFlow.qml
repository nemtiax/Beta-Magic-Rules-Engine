import QtQuick
import QtQuick.Layouts

Flow {
    id: flow
    required property var cards
    property bool interactive: true
    property bool targetable: false
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)

    spacing: 7
    Repeater {
        model: cards
        delegate: CardItem {
            required property var modelData
            cardData: modelData
            interactive: flow.interactive
            targetable: flow.targetable && cardData.legalTarget
            onSelected: function(cardId) { flow.selected(cardId) }
            onActivated: function(cardId) { flow.activated(cardId) }
            onAbilityActivated: function(cardId, abilityIndex) {
                flow.abilityActivated(cardId, abilityIndex)
            }
            onInspected: function(cardData) { flow.inspected(cardData) }
        }
    }
}
