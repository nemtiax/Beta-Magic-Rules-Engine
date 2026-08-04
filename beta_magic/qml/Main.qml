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

    Dialog {
        id: timeVaultPicker
        anchors.centerIn: parent
        implicitWidth: 420
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.timeVaultChoice
        title: gameState.timeVaultPlayer + "'s upcoming turn"

        contentItem: ColumnLayout {
            spacing: 8
            Label {
                text: "Take the turn, or skip it to ready one Time Vault on your following turn."
                color: "#ffffff"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Repeater {
                model: gameState.timeVaultChoices
                Button {
                    required property var modelData
                    text: modelData.label
                    Layout.fillWidth: true
                    onClicked: gameBridge.chooseTimeVaultTurn(modelData.id)
                }
            }
            Button {
                text: "Take the turn"
                Layout.fillWidth: true
                onClicked: gameBridge.chooseTimeVaultTurn("")
            }
        }
    }

    Dialog {
        id: xPicker
        anchors.centerIn: parent
        implicitWidth: 360
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.choosingX
        title: "Choose X for " + gameState.xCardName

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: "Affordable range: 0\u2013" + gameState.xMaximum
                color: "#ffffff"
            }
            RowLayout {
                Button {
                    text: "\u2212"
                    enabled: gameState.xValue > 0
                    onClicked: gameBridge.adjustX(-1)
                }
                Label {
                    text: "X = " + gameState.xValue
                    color: "#ffd978"
                    font.bold: true
                    font.pixelSize: 22
                    horizontalAlignment: Text.AlignHCenter
                    Layout.preferredWidth: 100
                }
                Button {
                    text: "+"
                    enabled: gameState.xValue < gameState.xMaximum
                    onClicked: gameBridge.adjustX(1)
                }
            }
            RowLayout {
                Button {
                    text: "Cancel"
                    onClicked: gameBridge.cancelXCast()
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "Cast"
                    onClicked: gameBridge.confirmXCast()
                }
            }
        }
    }

    Dialog {
        id: landTypePicker
        anchors.centerIn: parent
        implicitWidth: 360
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.choosingLandType
        title: "Choose a land type for " + gameState.landTypeCardName

        contentItem: ColumnLayout {
            spacing: 8
            Repeater {
                model: gameState.landTypeChoices
                Button {
                    required property string modelData
                    text: modelData
                    Layout.fillWidth: true
                    onClicked: gameBridge.chooseLandType(modelData)
                }
            }
            Button {
                text: "Cancel"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.cancelLandTypeChoice()
            }
        }
    }

    Dialog {
        id: modePicker
        anchors.centerIn: parent
        implicitWidth: 360
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.choosingMode
        title: "Choose how to cast " + gameState.modeCardName

        contentItem: ColumnLayout {
            spacing: 8
            Repeater {
                model: gameState.modeChoices
                Button {
                    required property string modelData
                    text: modelData
                    Layout.fillWidth: true
                    onClicked: gameBridge.chooseCastingMode(modelData)
                }
            }
            Button {
                text: "Cancel"
                Layout.alignment: Qt.AlignRight
                onClicked: gameBridge.cancelCastingMode()
            }
        }
    }

    Dialog {
        id: redirectionAmountPicker
        anchors.centerIn: parent
        implicitWidth: 360
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: gameState.choosingRedirectionAmount
        title: "Choose damage to redirect"

        contentItem: ColumnLayout {
            spacing: 12
            RowLayout {
                Button {
                    text: "\u2212"
                    enabled: gameState.redirectionAmount > 1
                    onClicked: gameBridge.adjustRedirectionAmount(-1)
                }
                Label {
                    text: gameState.redirectionAmount
                    color: "#ffd978"
                    font.bold: true
                    font.pixelSize: 22
                    horizontalAlignment: Text.AlignHCenter
                    Layout.preferredWidth: 100
                }
                Button {
                    text: "+"
                    enabled: gameState.redirectionAmount
                             < gameState.redirectionMaximum
                    onClicked: gameBridge.adjustRedirectionAmount(1)
                }
            }
            RowLayout {
                Button {
                    text: "Back"
                    onClicked: gameBridge.cancelRedirectionAmount()
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "Redirect"
                    onClicked: gameBridge.confirmRedirectionAmount()
                }
            }
        }
    }

    Connections {
        target: gameBridge
        function onStateChanged() { window.gameState = gameBridge.state }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        ColumnLayout {
            Layout.preferredWidth: 170
            Layout.minimumWidth: 150
            Layout.fillHeight: true
            spacing: 12

            PlayerStatus {
                Layout.fillWidth: true
                Layout.fillHeight: true
                playerData: gameState.opponent
                ownView: false
                onTargeted: function(playerId) { gameBridge.targetPlayer(playerId) }
            }
            PlayerStatus {
                Layout.fillWidth: true
                Layout.fillHeight: true
                playerData: gameState.perspective
                ownView: true
                onTargeted: function(playerId) { gameBridge.targetPlayer(playerId) }
            }
        }

        ScrollView {
            id: gameScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth

            ColumnLayout {
                width: gameScroll.availableWidth
                // Fill the viewport when there is spare room, but retain the
                // natural content height (and therefore scrolling) in a short
                // window or when contextual controls make the command bar tall.
                height: Math.max(implicitHeight, gameScroll.availableHeight)
                spacing: 9

                ZonePanel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 190
                    Layout.preferredHeight: 200
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
                            Label {
                                text: gameState.message
                                color: "#ffd978"
                                wrapMode: Text.WordWrap
                                Layout.maximumWidth: 430
                            }
                            Button {
                                visible: gameState.canAdvance
                                text: gameState.advanceLabel
                                onClicked: gameBridge.advance()
                            }
                            Button {
                                visible: gameState.canDiscard
                                text: gameState.effectDiscardRequired
                                      ? "Discard " + gameState.effectDiscardCount
                                        + " for " + gameState.effectDiscardPlayer
                                      : "Discard selected"
                                onClicked: gameBridge.discardSelected()
                            }
                            Button {
                                text: "Switch perspective"
                                onClicked: gameBridge.switchPerspective()
                            }
                            Button { text: "New game"; onClicked: gameBridge.newGame() }
                        }
                        RowLayout {
                            visible: gameState.contextActionsVisible
                            Button {
                                visible: gameState.canBeginAttack
                                text: "Begin attack"
                                onClicked: gameBridge.beginCombat()
                            }
                            Button {
                                visible: gameState.canDeclareAttackers
                                text: "Declare attackers"
                                onClicked: gameBridge.declareAttackers()
                            }
                            ComboBox {
                                id: attackTarget
                                visible: gameState.canDeclareBlockers
                                Layout.preferredWidth: 230
                                model: gameState.attackers
                                textRole: "label"
                                valueRole: "id"
                            }
                            CheckBox {
                                id: blockSecondAttacker
                                visible: gameState.canDeclareBlockers
                                text: "Block two"
                            }
                            ComboBox {
                                id: secondAttackTarget
                                visible: gameState.canDeclareBlockers
                                         && blockSecondAttacker.checked
                                Layout.preferredWidth: 230
                                model: gameState.attackers
                                textRole: "label"
                                valueRole: "id"
                            }
                            Button {
                                visible: gameState.canDeclareBlockers
                                text: "Declare blockers"
                                onClicked: gameBridge.declareBlockers(
                                    attackTarget.currentIndex >= 0
                                    ? attackTarget.currentValue : "",
                                    blockSecondAttacker.checked
                                    && secondAttackTarget.currentIndex >= 0
                                    ? secondAttackTarget.currentValue : ""
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
                                visible: gameState.priorityRequired
                                enabled: gameState.hasPriority
                                text: "Pass priority"
                                onClicked: gameBridge.passPriority()
                            }
                            Button {
                                visible: gameState.priorityRequired
                                enabled: gameState.hasPriority
                                         && !gameState.autoPassingTurn
                                text: "Auto-pass turn"
                                onClicked: gameBridge.autoPassTurn()
                            }
                            Label {
                                visible: gameState.priorityRequired
                                text: "Priority: " + gameState.priorityPlayer
                                color: "#cbd2da"
                                font.bold: true
                            }
                            Item { Layout.fillWidth: true }
                        }
                        Label {
                            visible: gameState.timedEvent
                            text: "Pending timed event: " + gameState.timedEvent
                            color: "#f2c66d"
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        RowLayout {
                            visible: gameState.targeting
                                     && gameState.stackCards.length > 0
                            Label {
                                text: "Spells being cast:"
                                color: "#f2c66d"
                                font.bold: true
                            }
                            Repeater {
                                model: gameState.stackCards
                                Button {
                                    required property var modelData
                                    text: modelData.label
                                    enabled: modelData.legalTarget
                                    onClicked: gameBridge.toggleCard(modelData.id)
                                }
                            }
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
                        RowLayout {
                            visible: gameState.choosingPrevention
                            Label {
                                text: "Choose damage to prevent ("
                                      + gameState.preventionRemaining + " remaining):"
                                color: "#9fd6a8"
                                font.bold: true
                            }
                            Repeater {
                                model: gameState.damagePacketChoices
                                delegate: Button {
                                    required property var modelData
                                    text: modelData.label
                                    onClicked: gameBridge.chooseDamagePacket(modelData.id)
                                }
                            }
                            Button {
                                text: "Done"
                                visible: gameState.preventionPaid
                                onClicked: gameBridge.finishPrevention()
                            }
                            Button {
                                text: "Cancel"
                                visible: !gameState.preventionPaid
                                onClicked: gameBridge.cancelPrevention()
                            }
                        }
                        RowLayout {
                            visible: gameState.choosingRedirection
                            Label {
                                text: "Choose creature damage to redirect:"
                                color: "#9fd6a8"
                                font.bold: true
                            }
                            Repeater {
                                model: gameState.redirectionPacketChoices
                                delegate: Button {
                                    required property var modelData
                                    text: modelData.label
                                    onClicked: gameBridge.chooseRedirectionPacket(
                                                   modelData.id)
                                }
                            }
                            Button {
                                text: "Cancel"
                                onClicked: gameBridge.cancelRedirection()
                            }
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
                        Label {
                            visible: gameState.rulesEvents.length > 0
                            text: "Catchable event"
                                  + (gameState.rulesEvents.length > 1 ? "s: " : ": ")
                                  + gameState.rulesEvents.join("  ·  ")
                            color: "#9fd6a8"
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }

                ZonePanel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 190
                    Layout.preferredHeight: 200
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
                HandPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 88
                    playerData: gameState.perspective
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
