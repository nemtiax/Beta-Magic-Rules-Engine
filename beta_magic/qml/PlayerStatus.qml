import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: status
    required property var playerData
    property bool ownView: false
    signal targeted(string playerId)

    padding: 12
    background: Rectangle {
        color: status.ownView ? "#252c35" : "#20252d"
        border.color: status.ownView ? "#729fcf" : "#414b59"
        radius: 8
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Label {
            Layout.fillWidth: true
            text: playerData.name
            color: "#f1f3f5"
            font.bold: true
            font.pixelSize: 17
            wrapMode: Text.WordWrap
        }
        Label {
            text: status.ownView ? "Your perspective" : "Opponent"
            color: status.ownView ? "#9ec7ef" : "#aeb7c2"
            font.pixelSize: 12
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: "#536171"
        }
        Label {
            text: "Life"
            color: "#aeb7c2"
            font.bold: true
        }
        Label {
            text: playerData.life
            color: "#ffffff"
            font.bold: true
            font.pixelSize: 28
        }
        Label {
            text: "Library  " + playerData.libraryCount
            color: "#cbd2da"
        }
        Label {
            text: "Hand  " + playerData.handCount
            color: "#cbd2da"
        }
        Label {
            Layout.fillWidth: true
            text: "Mana  " + (playerData.mana || "—")
            color: "#ffd978"
            font.bold: true
            wrapMode: Text.WordWrap
        }
        Item { Layout.fillHeight: true }
        Button {
            visible: playerData.legalTarget
            Layout.fillWidth: true
            text: "Target player"
            onClicked: status.targeted(playerData.id)
        }
    }
}
