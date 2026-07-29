import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1740
    height: 900
    minimumWidth: 1250
    minimumHeight: 700
    title: "Beta Magic · Rules Engine"
    color: "#101419"

    property var gameState: gameBridge.state
    property var inspectedCard: null

    Connections {
        target: gameBridge
        function onStateChanged() { window.gameState = gameBridge.state }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        ScrollView {
            id: gameScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth

            ColumnLayout {
                width: gameScroll.availableWidth
                spacing: 9

                PlayerPanel {
                    Layout.fillWidth: true
                    playerData: gameState.opponent
                    ownView: false
                    onTargeted: function(playerId) { gameBridge.targetPlayer(playerId) }
                    onInspected: function(cardData) { window.inspectedCard = cardData }
                }
                ZonePanel {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 245
                    playerData: gameState.opponent
                    interactive: false
                    targeting: gameState.targeting
                    frontAtBottom: true
                    onSelected: function(cardId) { gameBridge.toggleCard(cardId) }
                    onInspected: function(cardData) { window.inspectedCard = cardData }
                }

                Frame {
                    Layout.fillWidth: true
                    background: Rectangle {
                        color: "#29313b"
                        border.color: "#536171"
                        radius: 9
                    }
                    ColumnLayout {
                        anchors.fill: parent
                        RowLayout {
                            Label {
                                text: "Turn " + gameState.turn + " · " + gameState.phase
                                      + " · Active: " + gameState.activePlayer
                                      + (gameState.combatStep
                                         ? " · Combat: " + gameState.combatStep : "")
                                color: "#ffffff"
                                font.bold: true
                                font.pixelSize: 17
                            }
                            Item { Layout.fillWidth: true }
                            Button { text: "Advance"; onClicked: gameBridge.advance() }
                            Button {
                                text: "Discard selected"
                                onClicked: gameBridge.discardSelected()
                            }
                            Button {
                                text: "Switch perspective"
                                onClicked: gameBridge.switchPerspective()
                            }
                            Button { text: "New game"; onClicked: gameBridge.newGame() }
                        }
                        RowLayout {
                            Button {
                                text: "Begin attack"
                                onClicked: gameBridge.beginCombat()
                            }
                            Button {
                                text: "Declare attackers"
                                onClicked: gameBridge.declareAttackers()
                            }
                            ComboBox {
                                id: attackTarget
                                Layout.preferredWidth: 230
                                model: gameState.attackers
                                textRole: "label"
                                valueRole: "id"
                            }
                            Button {
                                text: "Declare blockers"
                                onClicked: gameBridge.declareBlockers(
                                    attackTarget.currentIndex >= 0
                                    ? attackTarget.currentValue : ""
                                )
                            }
                            Button {
                                visible: gameState.targeting
                                text: "Cancel target"
                                onClicked: gameBridge.cancelTarget()
                            }
                            Button {
                                visible: gameState.upkeepPaymentRequired
                                         && gameState.upkeepPaymentPlayer
                                            === gameState.perspective.id
                                enabled: gameState.canPayUpkeep
                                text: "Pay upkeep"
                                onClicked: gameBridge.chooseUpkeepPayment(true)
                            }
                            Button {
                                visible: gameState.upkeepPaymentRequired
                                         && gameState.upkeepPaymentPlayer
                                            === gameState.perspective.id
                                text: "Decline upkeep"
                                onClicked: gameBridge.chooseUpkeepPayment(false)
                            }
                            Button {
                                visible: gameState.stack.length > 0
                                         || gameState.timedEvent
                                         || gameState.damageWindow
                                         || gameState.destructionWindow
                                enabled: gameState.hasPriority
                                text: "Pass priority"
                                onClicked: gameBridge.passPriority()
                            }
                            Label {
                                visible: gameState.stack.length > 0
                                         || gameState.timedEvent
                                         || gameState.damageWindow
                                         || gameState.destructionWindow
                                text: "Priority: " + gameState.priorityPlayer
                                color: "#cbd2da"
                                font.bold: true
                            }
                            Item { Layout.fillWidth: true }
                            Label {
                                text: gameState.message
                                color: "#ffd978"
                                wrapMode: Text.WordWrap
                                Layout.maximumWidth: 600
                            }
                        }
                        Label {
                            visible: gameState.timedEvent
                            text: "Pending timed event: " + gameState.timedEvent
                            color: "#f2c66d"
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Label {
                            visible: gameState.damageWindow
                            text: gameState.damageWindow + " window — "
                                  + gameState.damagePackets.join("  +  ")
                            color: "#ef9f76"
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Label {
                            visible: gameState.destructionWindow
                            text: "Regeneration window — destroy "
                                  + gameState.destructionTargets.join(", ")
                            color: "#ef9f76"
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Label {
                            visible: gameState.stack.length > 0
                            text: "Current batch (declaration order): "
                                  + gameState.stack.join("  +  ")
                            color: "#f2c66d"
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                ZonePanel {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 245
                    playerData: gameState.perspective
                    interactive: true
                    targeting: gameState.targeting
                    frontAtBottom: false
                    onSelected: function(cardId) { gameBridge.toggleCard(cardId) }
                    onActivated: function(cardId) { gameBridge.activateCard(cardId) }
                    onAbilityActivated: function(cardId, abilityIndex) {
                        gameBridge.activateAbility(cardId, abilityIndex)
                    }
                    onInspected: function(cardData) { window.inspectedCard = cardData }
                }
                PlayerPanel {
                    Layout.fillWidth: true
                    playerData: gameState.perspective
                    ownView: true
                    onTargeted: function(playerId) { gameBridge.targetPlayer(playerId) }
                    onSelected: function(cardId) { gameBridge.toggleCard(cardId) }
                    onActivated: function(cardId) { gameBridge.activateCard(cardId) }
                    onAbilityActivated: function(cardId, abilityIndex) {
                        gameBridge.activateAbility(cardId, abilityIndex)
                    }
                    onInspected: function(cardData) { window.inspectedCard = cardData }
                }
            }
        }

        CardPreview {
            Layout.preferredWidth: 320
            Layout.fillHeight: true
            cardData: window.inspectedCard
        }
    }
}
