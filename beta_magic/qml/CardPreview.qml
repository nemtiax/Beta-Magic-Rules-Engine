import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: preview
    property var cardData: null

    padding: 14
    background: Rectangle {
        color: "#181d23"
        border.color: "#536171"
        radius: 9
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        Label {
            text: "Card preview"
            color: "#e5e9ef"
            font.bold: true
            font.pixelSize: 16
        }

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 280
            Layout.preferredHeight: 390
            radius: 14
            color: preview.cardData ? preview.cardData.background : "#252c35"
            border.color: preview.cardData ? preview.cardData.foreground : "#536171"
            border.width: 3

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: preview.cardData ? preview.cardData.name : "Mouse over a card"
                        color: preview.cardData ? preview.cardData.foreground : "#aeb7c2"
                        font.bold: true
                        font.pixelSize: 20
                        wrapMode: Text.WordWrap
                    }
                    Label {
                        text: preview.cardData ? preview.cardData.manaCost : ""
                        color: preview.cardData ? preview.cardData.foreground : "#aeb7c2"
                        font.bold: true
                        font.pixelSize: 18
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: preview.cardData ? preview.cardData.foreground : "#536171"
                    opacity: 0.55
                }

                Label {
                    Layout.fillWidth: true
                    text: preview.cardData ? preview.cardData.typeLine : ""
                    color: preview.cardData ? preview.cardData.foreground : "#aeb7c2"
                    font.bold: true
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    visible: preview.cardData && preview.cardData.attachedTo
                    text: preview.cardData
                          ? "Enchanting " + preview.cardData.attachedTo : ""
                    color: preview.cardData ? preview.cardData.foreground : "#aeb7c2"
                    font.bold: true
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 7
                    color: "#25ffffff"
                    border.color: "#45ffffff"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        Label {
                            Layout.fillWidth: true
                            text: preview.cardData
                                  ? (preview.cardData.rulesText
                                     || preview.cardData.abilities)
                                  : "The last card you mouse over will remain here."
                            color: preview.cardData
                                   ? preview.cardData.foreground : "#aeb7c2"
                            font.pixelSize: 16
                            wrapMode: Text.WordWrap
                            verticalAlignment: Text.AlignTop
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            visible: preview.cardData && !!preview.cardData.combatDetail
                            color: preview.cardData
                                   ? preview.cardData.foreground : "#536171"
                            opacity: 0.4
                        }

                        Label {
                            Layout.fillWidth: true
                            visible: preview.cardData && !!preview.cardData.combatDetail
                            text: preview.cardData ? preview.cardData.combatDetail : ""
                            color: preview.cardData
                                   ? preview.cardData.foreground : "#aeb7c2"
                            font.pixelSize: 14
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }

                        Item { Layout.fillHeight: true }
                    }
                }

                Label {
                    Layout.alignment: Qt.AlignRight
                    visible: preview.cardData && preview.cardData.isCreature
                    text: preview.cardData
                          ? preview.cardData.power + "/" + preview.cardData.toughness
                            + (preview.cardData.damage
                               ? "  · " + preview.cardData.damage + " damage"
                               : "")
                          : ""
                    color: preview.cardData ? preview.cardData.foreground : "#aeb7c2"
                    font.bold: true
                    font.pixelSize: 18
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: preview.cardData && preview.cardData.tapped ? "Tapped" : ""
            color: "#ffd978"
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
        }

        Item { Layout.fillHeight: true }
    }
}
