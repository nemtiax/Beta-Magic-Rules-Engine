import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: zone
    required property var playerData
    property bool interactive: false
    property bool selectionOnly: false
    property bool frontAtBottom: false
    property bool targeting: false
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)

    background: Rectangle {
        color: "#181d23"
        border.color: "#39434f"
        radius: 8
    }

    RowLayout {
        anchors.fill: parent
        spacing: 12
        GridLayout {
            columns: 1
            Layout.fillWidth: true
            Layout.minimumWidth: 480
            Label {
                Layout.row: zone.frontAtBottom ? 3 : 0
                text: "In play · creatures and other permanents"
                color: "#e5e9ef"
                font.bold: true
            }
            CardFlow {
                Layout.row: zone.frontAtBottom ? 4 : 1
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: implicitHeight
                cards: playerData.battlefieldNonlands
                edgeInset: 8
                interactive: zone.interactive
                selectionOnly: zone.selectionOnly
                targetable: zone.targeting
                onSelected: function(cardId) { zone.selected(cardId) }
                onActivated: function(cardId) { zone.activated(cardId) }
                onAbilityActivated: function(cardId, abilityIndex) {
                    zone.abilityActivated(cardId, abilityIndex)
                }
                onInspected: function(cardData) { zone.inspected(cardData) }
            }
            Rectangle {
                Layout.row: 2
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: "#39434f"
            }
            Label {
                Layout.row: zone.frontAtBottom ? 0 : 3
                text: "Lands"
                color: "#bfc7d1"
                font.bold: true
            }
            LandFlow {
                Layout.row: zone.frontAtBottom ? 1 : 4
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: implicitHeight
                columns: playerData.battlefieldLandColumns
                edgeInset: 8
                interactive: zone.interactive
                selectionOnly: zone.selectionOnly
                targetable: zone.targeting
                onSelected: function(cardId) { zone.selected(cardId) }
                onActivated: function(cardId) { zone.activated(cardId) }
                onAbilityActivated: function(cardId, abilityIndex) {
                    zone.abilityActivated(cardId, abilityIndex)
                }
                onInspected: function(cardData) { zone.inspected(cardData) }
            }
        }
        ColumnLayout {
            Layout.preferredWidth: 232
            Layout.minimumWidth: 224
            Layout.maximumWidth: 250
            Layout.fillWidth: false
            Layout.fillHeight: true
            spacing: 7

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8

                ColumnLayout {
                    Layout.preferredWidth: 108
                    Layout.minimumWidth: 108
                    Layout.fillHeight: true
                    spacing: 5
                    Label {
                        text: "Graveyard · " + playerData.graveyardCount
                        color: "#e5e9ef"
                        font.bold: true
                    }
                    CardPile {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 72
                        cards: playerData.graveyard
                        targetable: zone.targeting
                        onSelected: function(cardId) { zone.selected(cardId) }
                        onInspected: function(cardData) { zone.inspected(cardData) }
                    }
                }

                ColumnLayout {
                    Layout.preferredWidth: 108
                    Layout.minimumWidth: 108
                    Layout.fillHeight: true
                    spacing: 5
                    Label {
                        text: "Set aside · " + playerData.exileCount
                        color: "#e5e9ef"
                        font.bold: true
                    }
                    CardPile {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 72
                        cards: playerData.exile
                        onInspected: function(cardData) { zone.inspected(cardData) }
                    }
                }
            }

            Rectangle {
                visible: playerData.anteCount > 0
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? 1 : 0
                color: "#39434f"
            }
            Label {
                visible: playerData.anteCount > 0
                text: "Ante · " + playerData.anteCount
                color: "#f2c66d"
                font.bold: true
            }
            CardFlow {
                visible: playerData.anteCount > 0
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? implicitHeight : 0
                Layout.minimumHeight: visible ? implicitHeight : 0
                cards: playerData.ante
                interactive: false
                targetable: zone.targeting
                onSelected: function(cardId) { zone.selected(cardId) }
                onInspected: function(cardData) { zone.inspected(cardData) }
            }
        }
    }
}
