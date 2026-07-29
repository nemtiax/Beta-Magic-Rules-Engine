import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: panel
    required property var playerData
    property bool ownView: false
    signal selected(string cardId)
    signal activated(string cardId)
    signal abilityActivated(string cardId, int abilityIndex)
    signal inspected(var cardData)
    signal targeted(string playerId)

    background: Rectangle {
        color: ownView ? "#252c35" : "#20252d"
        border.color: ownView ? "#729fcf" : "#414b59"
        radius: 8
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 7
        RowLayout {
            Layout.fillWidth: true
            Label {
                text: playerData.name + (ownView ? " · your perspective" : "")
                color: "#f1f3f5"
                font.bold: true
                font.pixelSize: 16
            }
            Item { Layout.fillWidth: true }
            Button {
                visible: playerData.legalTarget
                text: "Target player"
                onClicked: panel.targeted(playerData.id)
            }
        }
        Label {
            text: "Life " + playerData.life + "     Library " + playerData.libraryCount
                  + "     Mana " + playerData.mana
            color: "#cbd2da"
        }
        Label {
            text: "Hand · " + playerData.handCount
            color: "#dfe4ea"
            font.bold: true
        }
        CardFlow {
            Layout.fillWidth: true
            visible: ownView
            cards: playerData.hand
            interactive: true
            onSelected: function(cardId) { panel.selected(cardId) }
            onActivated: function(cardId) { panel.activated(cardId) }
            onAbilityActivated: function(cardId, abilityIndex) {
                panel.abilityActivated(cardId, abilityIndex)
            }
            onInspected: function(cardData) { panel.inspected(cardData) }
        }
        Rectangle {
            visible: !ownView
            width: 160
            height: 42
            radius: 5
            color: "#343c47"
            border.color: "#596574"
            Label {
                anchors.centerIn: parent
                text: playerData.handCount + " hidden card(s)"
                color: "#cbd2da"
            }
        }
    }
}
