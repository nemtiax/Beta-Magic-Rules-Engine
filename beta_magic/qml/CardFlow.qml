import QtQuick
import QtQuick.Controls

Flickable {
    id: flow
    required property var cards
    property bool interactive: true
    property bool targetable: false
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)

    readonly property int maximumAttachments: {
        var maximum = 0
        for (var index = 0; index < cards.length; ++index) {
            var attachments = cards[index].attachments || []
            maximum = Math.max(maximum, attachments.length)
        }
        return maximum
    }
    implicitHeight: 72 + maximumAttachments * 18
    contentWidth: cardRow.implicitWidth
    contentHeight: height
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    flickableDirection: Flickable.HorizontalFlick
    ScrollBar.horizontal: ScrollBar {
        policy: flow.contentWidth > flow.width
                ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
    }

    Row {
        id: cardRow
        spacing: 7
        Repeater {
            model: cards
            delegate: AttachmentStack {
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
}
