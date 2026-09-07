import QtQuick
import QtQuick.Controls

Flickable {
    id: flow
    required property var columns
    property bool interactive: true
    property bool selectionOnly: false
    property bool targetable: false
    property int edgeInset: 0
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)

    implicitHeight: Math.max(72, columnRow.implicitHeight) + edgeInset * 2
    contentWidth: columnRow.implicitWidth + edgeInset * 2
    contentHeight: Math.max(height, columnRow.implicitHeight + edgeInset * 2)
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    flickableDirection: Flickable.HorizontalFlick
    ScrollBar.horizontal: ScrollBar {
        policy: flow.contentWidth > flow.width
                ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
    }

    Row {
        id: columnRow
        x: flow.edgeInset
        y: flow.edgeInset
        spacing: 7

        Repeater {
            model: flow.columns
            delegate: CardStack {
                required property var modelData
                cards: modelData.cards
                cardsInteractive: flow.interactive
                selectionOnly: flow.selectionOnly
                targetable: flow.targetable
                onSelected: function(cardId) { flow.selected(cardId) }
                onActivated: function(cardId) { flow.activated(cardId) }
                onAbilityActivated: function(cardId, abilityIndex) {
                    flow.abilityActivated(cardId, abilityIndex)
                }
                onInspected: function(cardData) { flow.inspected(cardData) }
            }
        }
    }
}
