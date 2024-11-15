#SingleInstance, Force

; Inicializa uma flag global para controlar o loop de movimento do mouse
isMoving := false

; Lê a duração a partir dos argumentos de linha de comando
if (0 >= 1) { ; Se houver pelo menos um argumento
    Duration := %1% ; Primeiro argumento em milissegundos
} else {
    Duration := 15000 ; Padrão para 2 horas em milissegundos
}

; Define o caminho para o arquivo de sinalização
FlagFilePath := A_ScriptDir "\mouse_moving.flag"

; Inicia o movimento do mouse automaticamente
StartMouseMovement()

Return ; Fim da seção de auto-execução

StartMouseMovement() {
    global isMoving, FlagFilePath, Duration, StartTime

    if (!isMoving) {
        isMoving := true
        ; Inicializa StartTime
        StartTime := A_TickCount
        ; Cria o arquivo de sinalização
        FileAppend,, %FlagFilePath%
        ; Inicia o loop de movimento do mouse
        SetTimer, MoveMouse, 10
    }
}

StopMouseMovement() {
    global isMoving, FlagFilePath

    if (isMoving) {
        isMoving := false
        ; Para o loop de movimento do mouse
        SetTimer, MoveMouse, Off
        StartTime := 0
        ; Deleta o arquivo de sinalização
        FileDelete, %FlagFilePath%
        ExitApp ; Encerra o script AHK após parar o movimento
    }
}

MoveMouse:
    ; Garante que o movimento só ocorre se isMoving for verdadeiro
    if (!isMoving)
        return

    CoordMode, Mouse, Screen
    MouseGetPos, mouseX, mouseY

    ; Define os incrementos de movimento
    movex := -20
    movey := 20

    ; Atualiza a direção do movimento com base nas bordas da tela
    if (mouseX > 1890) {
        movex := -20
    }
    else if (mouseX <= 0) {
        movex := 20
    }

    if (mouseY > 1020) {
        movey := -20
    }
    else if (mouseY <= 0) {
        movey := 20
    }

    ; Move o mouse relativo à posição atual
    MouseMove, %movex%, %movey%, 0, R

    ; Implementa uma duração máxima
    if (!StartTime) {
        StartTime := A_TickCount
    }

    ; Verifica se a duração foi excedida
    if (A_TickCount - StartTime > Duration) {
        StopMouseMovement()
    }
Return

; Hotkey para parar o movimento do mouse: Ctrl + K
^k::
    StopMouseMovement()
Return
